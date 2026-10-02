"""Interface web locale : http://localhost:7860 (accessible uniquement depuis ce PC)."""

import base64
import hashlib
import mimetypes
import os
import json
import re
import secrets
import subprocess
import sys
import threading
import urllib.parse
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import ai_inpaint, config, remote, scheduler, system, updater
from .core import Agent, Brain

# empreinte du code : permet de savoir si le Jarvis déjà lancé est une ancienne version
CODE_VERSION = hashlib.sha1(b"".join(p.read_bytes() for p in sorted(Path(__file__).parent.glob("*.py")))).hexdigest()[:12]
ARGV = [sys.executable, os.path.abspath(sys.argv[0])] + sys.argv[1:]
TOKEN_FILE = config.HOME / "server.token"   # secret local : seul ce PC peut demander l'arrêt du serveur

INDEX = Path(__file__).with_name("index.html")
LOGIN = Path(__file__).with_name("login.html")


class WebUI:
    def __init__(self):
        self.events, self.cond = [], threading.Condition()
        self.pending = {}

    def emit(self, **event):
        with self.cond:
            event["i"] = len(self.events)
            self.events.append(event)
            self.cond.notify_all()

    def since(self, i, wait=20):
        with self.cond:
            self.cond.wait_for(lambda: len(self.events) > i, timeout=wait)
            return self.events[i:]

    def token(self, text):
        self.emit(type="token", text=text)

    def tool_start(self, name, args):
        self.emit(type="tool", name=name, args=args)

    def tool_end(self, name, result):
        self.emit(type="result", name=name, text=result[:4000])

    def done(self, text):
        self.emit(type="done")

    def info(self, text, level="info"):
        self.emit(type="info", text=text, level=level)

    def plan(self, steps):
        self.emit(type="plan", steps=steps)

    def confirm(self, action):
        cid = uuid.uuid4().hex
        ready = threading.Event()
        self.pending[cid] = [ready, False]
        self.emit(type="confirm", id=cid, action=action)
        ready.wait()
        return self.pending.pop(cid)[1]

    def answer(self, cid, value):
        if cid in self.pending:
            self.pending[cid][1] = value
            self.pending[cid][0].set()
            self.emit(type="confirmed", id=cid)


class App:
    def __init__(self, cfg, workdir, port=7860):
        self.cfg, self.ui, self.port = cfg, WebUI(), port
        self.bound_remote = False     # le serveur écoute-t-il le réseau local ?
        self.restart_server = None    # rappel fourni par serve() pour réouvrir le serveur
        self.relaunch = None          # rappel fourni par serve() pour relancer tout Jarvis (après une mise à jour)
        self.brain = Brain(cfg, self.ui)
        self.workdir = workdir
        self.agent = Agent(self.brain, self.ui, cfg, workdir, auto=cfg["auto"])
        self.busy = False
        self.queue = []
        scheduler.start(self.on_due)

    def on_due(self, item):
        if item["kind"] == "rappel":
            system.notify("Rappel de Jarvis", item["task"])
            self.ui.info(f"⏰ Rappel : {item['task']}", "warn")
        else:
            self.queue.append(item["task"])
        if self.queue and not self.busy:
            self.send("[Tâche planifiée, exécute-la puis résume le résultat] " + self.queue.pop(0), [])

    # ---------------------------------------------------------- studio photo --
    IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

    def _roots(self):
        home = Path.home()
        return [Path(self.agent.tools.workdir), config.HOME] + [home / d for d in ("Pictures", "Images", "Desktop",
                                                                              "Downloads", "Documents", "OneDrive")]

    def allowed_image(self, path):
        p = Path(path).expanduser().resolve()
        ok = p.suffix.lower() in self.IMG_EXT and p.is_file()
        return p if ok and any(p.is_relative_to(r.resolve()) for r in self._roots() if r.exists()) else None

    def recent_images(self, limit=80):
        found = []
        for root in self._roots():
            if not root.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                depth = len(Path(dirpath).relative_to(root).parts)
                dirnames[:] = [] if depth >= 3 else [d for d in dirnames if not d.startswith((".", "$")) and d != "node_modules"]
                for f in filenames:
                    if Path(f).suffix.lower() in self.IMG_EXT:
                        p = Path(dirpath, f)
                        try:
                            found.append((p.stat().st_mtime, str(p)))
                        except OSError:
                            pass
                if len(found) > 3000:
                    break
        found.sort(reverse=True)
        return [{"path": p, "name": Path(p).name} for _, p in dict((p, (t, p)) for t, p in found).values()][:limit]

    def save_image(self, name, data, fmt=None, quality=92, source_path=None, source_data=None,
                   keep_meta=True, keep_gps=False, download=False):
        """Encode l'image finale (profil de couleurs, infos de la photo) puis l'enregistre ou la renvoie."""
        from . import photo, photo_export
        if photo.ensure_pillow():  # Pillow absent et impossible à installer : on garde l'image telle quelle
            m = re.match(r"data:image/(png|jpeg|webp);base64,(.*)", data or "", re.S)
            raw, ext = base64.b64decode(m.group(2)), {"jpeg": "jpg"}.get(m.group(1), m.group(1))
        else:
            src = str(self.allowed_image(source_path)) if source_path and self.allowed_image(source_path) else None
            raw, ext = photo_export.encode(data, fmt or "jpeg", quality, src, source_data, keep_meta, keep_gps)
        stem = photo_export.safe_stem(name)
        if download:
            mime = {"jpg": "jpeg"}.get(ext, ext)
            return {"data": f"data:image/{mime};base64," + base64.b64encode(raw).decode(), "name": f"{stem}.{ext}",
                    "size": len(raw)}
        folder = Path(self.agent.tools.workdir) / "photos"
        folder.mkdir(parents=True, exist_ok=True)
        dest, n = folder / f"{stem}.{ext}", 2
        while dest.exists():
            dest, n = folder / f"{stem} ({n}).{ext}", n + 1
        dest.write_bytes(raw)
        return {"path": str(dest), "size": len(raw)}

    def state(self):
        return {"provider": self.brain.name, "model": self.brain.llm.model, "auto": self.agent.tools.auto,
                "busy": self.busy, "workdir": str(self.agent.tools.workdir),
                "providers": {n: config.available(self.cfg, n) for n in self.cfg["providers"]},
                "email": (self.cfg.get("email") or {}).get("address", ""),
                "startup": system.startup_enabled(), "windows": system.WINDOWS,
                "remote": remote.enabled(self.cfg), "remote_active": self.bound_remote,
                "has_pin": bool((self.cfg.get("remote") or {}).get("pin_hash")),
                "addresses": remote.addresses(self.port) if self.bound_remote else []}

    def send(self, text, images):
        if self.busy:
            return {"error": "Jarvis travaille déjà. Attends ou clique sur Stop."}
        for img in images:  # les images jointes sont enregistrées et confiées à l'outil de vision
            m = re.match(r"data:image/(\w+);base64,(.*)", img.get("data", ""), re.S)
            if not m:
                continue
            config.CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
            ext = "jpg" if m.group(1) == "jpeg" else m.group(1)
            path = config.CAPTURES_DIR / f"jointe-{uuid.uuid4().hex[:8]}.{ext}"
            path.write_bytes(base64.b64decode(m.group(2)))
            text += f"\n[Image jointe par l'utilisateur : {path} — utilise look_at_image pour la voir]"
        self.ui.emit(type="user", text=text)

        self.busy = True

        def work():
            try:
                self.agent.run(text)
            except Exception as e:
                self.ui.info(f"Erreur : {e}", "error")
                self.ui.done("")
            finally:
                self.busy = False
                if self.queue:
                    self.send("[Tâche planifiée, exécute-la puis résume le résultat] " + self.queue.pop(0), [])
        threading.Thread(target=work, daemon=True).start()
        return {"ok": True}

    def command(self, cmd, arg):
        if cmd == "stop":
            self.agent.stop = True
            for cid in list(self.ui.pending):
                self.ui.answer(cid, False)
        elif cmd == "auto":
            self.agent.tools.auto = bool(arg)
        elif cmd == "new":
            self.agent = Agent(self.brain, self.ui, self.cfg, self.workdir, auto=self.agent.tools.auto)
        elif cmd == "provider":
            self.brain.use(arg)
            self.cfg["provider"] = arg
            config.save(self.cfg)
        elif cmd == "model":
            self.cfg["providers"][self.brain.name]["model"] = str(arg).strip()
            config.save(self.cfg)
            self.brain.use(self.brain.name)
        elif cmd == "key":
            name, key = arg.get("provider"), arg.get("key", "").strip()
            self.cfg["api_keys"][name] = key
            config.save(self.cfg)
        elif cmd == "email":
            address, password = arg.get("address", "").strip(), arg.get("password", "").strip()
            if address and password:
                self.cfg["email"] = {"address": address, "password": password}
            elif not address:
                self.cfg.pop("email", None)
            config.save(self.cfg)
        elif cmd == "email_test":
            from . import emailer
            return {**self.state(), "message": "Connexion réussie. Derniers e-mails :\n"
                    + emailer.list_emails(self.cfg, 3)}
        elif cmd == "startup":
            err = system.set_startup(bool(arg), updater.APP_DIR)
            if err:
                raise RuntimeError(err)
        elif cmd == "remote":
            if arg.get("pin"):
                remote.set_pin(self.cfg, arg["pin"])
            want = bool(arg.get("enabled"))
            if want and not (self.cfg.get("remote") or {}).get("pin_hash"):
                raise ValueError("Choisis d'abord un code PIN (au moins 6 chiffres).")
            self.cfg.setdefault("remote", {})["enabled"] = want
            config.save(self.cfg)
            if want != self.bound_remote and self.restart_server:
                self.restart_server()
            return {**self.state(), "remote_active": want, "addresses": remote.addresses(self.port) if want else []}
        elif cmd == "update":
            message = updater.update()
            if self.relaunch:
                self.relaunch()
                message = message.split(". ")[0] + ". Jarvis redémarre tout seul… la page va se recharger."
            return {**self.state(), "message": message, "restarting": bool(self.relaunch)}
        elif cmd == "listen":
            text, err = system.listen()
            return {"text": text, "error": err}
        return self.state()


def serve(cfg, workdir, port=7860, open_browser=True):
    app = None
    state = {"server": None, "again": True}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, body, ctype, code=200, headers=()):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in headers:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, code=200, headers=()):
            self._send(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", code, headers)

        def _body(self):
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")

        def _is_pc(self):
            return self.client_address[0] in ("127.0.0.1", "::1")

        def _authed(self):
            if self._is_pc():
                return True
            m = re.search(r"jarvis=([0-9a-f]{48})", self.headers.get("Cookie", ""))
            return bool(m) and remote.token_ok(m.group(1))

        def _same_origin(self):
            # protège contre les requêtes envoyées par d'autres sites ouverts dans le navigateur
            origin = self.headers.get("Origin")
            if origin is None:
                return True
            host = re.sub(r"^https?://", "", origin)
            return host == self.headers.get("Host") or re.match(r"^(localhost|127\.0\.0\.1)(:\d+)?$", host)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/version":
                return self._json({"version": CODE_VERSION})
            if path == "/manifest.json":
                return self._json({"name": "Jarvis", "short_name": "Jarvis", "start_url": "/", "display": "standalone",
                                   "background_color": "#05080f", "theme_color": "#05080f", "lang": "fr",
                                   "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                                             {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]})
            if path in ("/icon-192.png", "/icon-512.png", "/apple-touch-icon.png"):
                return self._send(_icon(512 if "512" in path else 192 if "192" in path else 180), "image/png")
            if not self._authed():
                if path == "/":
                    return self._send(LOGIN.read_bytes(), "text/html; charset=utf-8")
                return self._json({"error": "non autorisé"}, 401)
            if path == "/":
                self._send(INDEX.read_bytes(), "text/html; charset=utf-8")
            elif path in ("/studio.js", "/studio.css", "/inpaint.js"):
                self._send((Path(__file__).parent / path[1:]).read_bytes(),
                           "text/javascript; charset=utf-8" if path.endswith(".js") else "text/css; charset=utf-8")
            elif path == "/photo_folders":
                from . import batch
                self._json(batch.folders(app._roots()))
            elif path == "/photo_watch":
                from . import batch
                self._json(batch.watch_list(app.cfg))
            elif path == "/batch_status":
                from . import batch
                self._json(batch.status())
            elif path == "/ai_status":
                self._json(ai_inpaint.status())
            elif path == "/images":
                self._json(app.recent_images())
            elif path == "/file":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                p = app.allowed_image(q.get("path", [""])[0])
                if not p:
                    return self._json({"error": "fichier non autorisé"}, 403)
                self._send(p.read_bytes(), mimetypes.guess_type(p.name)[0] or "application/octet-stream")
            elif path == "/state":
                self._json(app.state())
            elif path == "/events":
                m = re.search(r"since=(\d+)", self.path)
                self._json(app.ui.since(int(m.group(1)) if m else 0))
            else:
                self._json({"error": "introuvable"}, 404)

        def do_POST(self):
            if self.path == "/quit":  # demandé par un Jarvis plus récent lancé sur ce PC
                data = self._body()
                try:
                    ok = secrets.compare_digest(str(data.get("token", "")), TOKEN_FILE.read_text().strip())
                except OSError:
                    ok = False
                if not ok:
                    return self._json({"error": "refusé"}, 403)
                self._json({"ok": True})
                state["quit"] = True
                threading.Timer(0.2, state["server"].shutdown).start()
                return
            if not self._same_origin():
                return self._json({"error": "origine refusée"}, 403)
            data = self._body()
            if self.path == "/login":
                ok, msg = remote.check_pin(app.cfg, data.get("pin"))
                if not ok:
                    return self._json({"error": msg}, 403)
                token = remote.new_token(self.headers.get("User-Agent", ""))
                return self._json({"ok": True}, headers=[("Set-Cookie", f"jarvis={token}; Path=/; HttpOnly; "
                                                          "SameSite=Strict; Max-Age=31536000")])
            if not self._authed():
                return self._json({"error": "non autorisé"}, 401)
            try:
                if self.path == "/send":
                    self._json(app.send(data.get("text", ""), data.get("images", [])))
                elif self.path == "/confirm":
                    app.ui.answer(data["id"], "always" if data.get("always") else bool(data.get("ok")))
                    self._json({"ok": True})
                elif self.path == "/ai_install":
                    self._json(ai_inpaint.install(deps_only=bool(data.get("deps_only")), pack=data.get("pack", "lama")))
                elif self.path == "/ai_upscale":
                    self._json({"image": ai_inpaint.upscale(data.get("image", ""), data.get("factor", 2),
                                                            data.get("quality", "fast"))})
                elif self.path == "/ai_enhance":
                    from . import enhance_ai
                    self._json(enhance_ai.enhance_data_url(data.get("image", ""), bool(data.get("best"))))
                elif self.path == "/ai_warmup":
                    ai_inpaint.warmup()
                    self._json({"ok": True})
                elif self.path == "/batch_start":
                    from . import batch
                    self._json(batch.start(data.get("folder", ""), bool(data.get("best"))))
                elif self.path == "/photo_watch":
                    from . import batch
                    self._json(batch.set_watch(app.cfg, data.get("folder", ""), bool(data.get("on", True)), bool(data.get("best"))))
                elif self.path == "/batch_cancel":
                    from . import batch
                    self._json(batch.cancel())
                elif self.path == "/convert_image":
                    from . import batch
                    self._json(batch.to_jpeg_data_url(data.get("image", "")))
                elif self.path == "/open_folder":
                    system.open_item(str(data.get("path", "")))
                    self._json({"ok": True})
                elif self.path == "/ai_faces":
                    self._json(ai_inpaint.restore_faces(data.get("image", ""), data.get("strength", 0.8)))
                elif self.path == "/ai_inpaint":
                    self._json({"image": ai_inpaint.inpaint(data.get("image", ""), data.get("mask", ""))})
                elif self.path == "/save_image":
                    self._json(app.save_image(data.get("name"), data.get("data"), data.get("fmt"), data.get("quality", 92),
                                              data.get("source_path"), data.get("source_data"),
                                              data.get("keep_meta", True), data.get("keep_gps", False), data.get("download", False)))
                elif self.path == "/command":
                    self._json(app.command(data.get("cmd"), data.get("arg")))
                else:
                    self._json({"error": "introuvable"}, 404)
            except Exception as e:
                self._json({"error": str(e)}, 400)

    url = f"http://localhost:{port}"
    # Sous Windows, SO_REUSEADDR laisserait deux Jarvis écouter le même port sans erreur
    ThreadingHTTPServer.allow_reuse_address = not system.WINDOWS

    def open_server():
        host = "0.0.0.0" if remote.enabled(cfg) else "127.0.0.1"
        server = ThreadingHTTPServer((host, port), Handler)
        if app:
            app.bound_remote = host == "0.0.0.0"
        return server

    try:
        state["server"] = open_server()
    except OSError:
        state["server"] = _replace_old(port, open_server)
        if not state["server"]:
            print(f"Jarvis tourne déjà : j'ouvre {url}")
            webbrowser.open(url)
            return
    token = secrets.token_hex(16)
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token)
    except OSError:
        pass
    app = App(cfg, workdir, port)
    app.bound_remote = remote.enabled(cfg)

    def relaunch():
        state["relaunch"] = True
        threading.Timer(1.0, state["server"].shutdown).start()
    app.relaunch = relaunch
    from . import batch
    batch.start_watcher(app.cfg)

    def restart():
        # appelé depuis une requête : on ferme le serveur dans un autre fil, la boucle ci-dessous le rouvre
        threading.Timer(0.3, state["server"].shutdown).start()
    app.restart_server = restart

    print(f"Jarvis est prêt sur {url}  (ferme cette fenêtre pour l'arrêter)")
    if app.bound_remote:
        print("Accès téléphone activé : " + ", ".join(a["url"] for a in remote.addresses(port)))
    if open_browser:
        threading.Timer(1, lambda: webbrowser.open(url)).start()
    try:
        while True:
            state["server"].serve_forever()
            state["server"].server_close()
            if state.get("quit"):
                print("Une version plus récente de Jarvis prend le relais.")
                os._exit(0)
            if state.get("relaunch"):
                argv = ARGV + ([] if "--no-browser" in ARGV else ["--no-browser"])
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if Path(sys.executable).stem.lower() == "pythonw" else 0
                subprocess.Popen(argv, cwd=str(updater.APP_DIR), creationflags=flags)
                os._exit(0)
            for _ in range(20):  # rouvre sur la nouvelle interface réseau
                try:
                    state["server"] = open_server()
                    break
                except OSError:
                    time.sleep(0.25)
            else:
                print("Impossible de rouvrir le serveur.")
                return
    except KeyboardInterrupt:
        pass


def _replace_old(port, open_server):
    """Un Jarvis tourne déjà sur ce port : si c'est une ancienne version, on le remplace par celle-ci."""
    import json as _json
    import urllib.request
    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(base + "/version", timeout=3) as r:
            if _json.loads(r.read()).get("version") == CODE_VERSION:
                return None  # même version : on garde celui qui tourne
    except Exception:
        pass  # ancienne version sans /version, ou serveur bloqué
    stopped = False
    try:
        req = urllib.request.Request(base + "/quit", data=_json.dumps({"token": TOKEN_FILE.read_text().strip()}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as r:
            stopped = r.status == 200
    except Exception:
        pass
    if not stopped and system.WINDOWS:
        # ancienne version : on arrête le processus Jarvis qui occupe le port (et seulement lui)
        system.powershell(
            f"$ids = (Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue).OwningProcess\n"
            "foreach ($i in $ids) { $p = Get-CimInstance Win32_Process -Filter \"ProcessId=$i\"\n"
            "  if ($p.CommandLine -like '*agent.py*') { Stop-Process -Id $i -Force } }", timeout=30)
    for _ in range(40):
        try:
            server = open_server()
            print("Ancienne version de Jarvis arrêtée : la nouvelle démarre.")
            return server
        except OSError:
            time.sleep(0.25)
    return None


_ICONS = {}


def _icon(size):
    if size not in _ICONS:
        _ICONS[size] = remote.icon_png(size)
    return _ICONS[size]

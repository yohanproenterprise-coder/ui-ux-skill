"""Photo Studio IA : le Studio photo de Jarvis en application autonome (sans l'assistant).

Amélioration en un clic, netteté renforcée, dossiers entiers, gomme magique, mise en scène de produit,
recadrage, texte, export. Tout tourne sur le PC ; seuls les décors créés par l'IA passent par internet.
Seuls des modèles d'IA autorisés en usage commercial sont proposés (pas de restauration de visages).
"""

import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_NAME = "Photo Studio IA"
VERSION = "1.0.0"
PORT = 7870
HERE = Path(__file__).resolve().parent
CODE = HERE.parent if (HERE.parent / "jarvis").is_dir() else HERE / "app"
sys.path.insert(0, str(CODE))

# données de l'application (réglages, modèles téléchargés) : séparées de Jarvis
if "JARVIS_HOME" not in os.environ:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    os.environ["JARVIS_HOME"] = str(Path(base) / "PhotoStudioIA")
Path(os.environ["JARVIS_HOME"]).mkdir(parents=True, exist_ok=True)
if sys.stdout is None or sys.stderr is None:   # lancé sans console (pythonw) : journal dans un fichier
    sys.stdout = sys.stderr = open(Path(os.environ["JARVIS_HOME"]) / "journal.txt", "a", encoding="utf-8", buffering=1)

from jarvis import gpu  # noqa: E402
gpu.activate_path()   # moteur carte graphique, s'il a été installé (avant tout chargement de l'IA)

from jarvis import ai_inpaint, batch, config, photo_export, system  # noqa: E402
import licence  # noqa: E402  (essai gratuit puis clé Lemon Squeezy)

# --- uniquement des modèles autorisés en usage commercial ---
for name in ("faces",):
    ai_inpaint.PACKS.pop(name, None)
    ai_inpaint.OPTIONAL.pop(name, None)
ai_inpaint.PACKS["enhance"] = list(ai_inpaint.PACKS["upmax"])
ai_inpaint.OPTIONAL.pop("enhance", None)
ai_inpaint.PACK_LABELS.update({"enhance": "IA d'amélioration (≈ 70 Mo)", "upmax": "IA qualité maximale (≈ 70 Mo)"})
ai_inpaint.UI_LABELS.update({"enhance": "L'IA d'amélioration (≈ 70 Mo)", "upmax": "L'IA qualité maximale (≈ 70 Mo)",
                             "sharp": "Le modèle de netteté le plus fin (≈ 67 Mo)",
                             "cutout": "L'IA de détourage (≈ 225 Mo)", "lama": "L'IA de retouche (≈ 92 Mo)"})
batch.APP_NAME = APP_NAME

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif"}
SAVE_DIR = Path.home() / "Pictures" / APP_NAME
last_ping = [time.time()]


def roots():
    home = Path.home()
    return [home / d for d in ("Pictures", "Images", "Desktop", "Downloads", "Documents", "OneDrive")] + [SAVE_DIR]


def allowed_image(path):
    try:
        p = Path(path).expanduser().resolve()
    except OSError:
        return None
    ok = p.suffix.lower() in IMG_EXT and p.is_file()
    return p if ok and any(p.is_relative_to(r.resolve()) for r in roots() if r.exists()) else None


def recent_images(limit=80):
    found = []
    for root in roots():
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            dirnames[:] = [] if depth >= 3 else [d for d in dirnames if not d.startswith((".", "$"))]
            for f in filenames:
                if Path(f).suffix.lower() in IMG_EXT - {".heic", ".heif"}:
                    p = Path(dirpath, f)
                    try:
                        found.append((p.stat().st_mtime, str(p)))
                    except OSError:
                        pass
            if len(found) > 3000:
                break
    found.sort(reverse=True)
    seen, out = set(), []
    for _, p in found:
        if p not in seen:
            seen.add(p)
            out.append({"path": p, "name": Path(p).name})
    return out[:limit]


def save_image(name, data, fmt=None, quality=92, source_path=None, source_data=None, keep_meta=True, keep_gps=False,
               download=False):
    import base64
    src = str(allowed_image(source_path)) if source_path and allowed_image(source_path) else None
    raw, ext = photo_export.encode(data, fmt or "jpeg", quality, src, source_data, keep_meta, keep_gps)
    stem = photo_export.safe_stem(name)
    if download:
        mime = {"jpg": "jpeg"}.get(ext, ext)
        return {"data": f"data:image/{mime};base64," + base64.b64encode(raw).decode(), "name": f"{stem}.{ext}",
                "size": len(raw)}
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    dest, n = SAVE_DIR / f"{stem}.{ext}", 2
    while dest.exists():
        dest, n = SAVE_DIR / f"{stem} ({n}).{ext}", n + 1
    dest.write_bytes(raw)
    return {"path": str(dest), "size": len(raw)}


def page():
    """Page de l'application : le design de Jarvis (styles et icônes), avec le Studio ouvert en plein écran."""
    index = (CODE / "jarvis" / "index.html").read_text(encoding="utf-8")
    head = index[:index.index("</svg>") + len("</svg>")]
    head = re.sub(r"<title>.*?</title>", f"<title>{APP_NAME}</title>", head, flags=re.S)
    head = re.sub(r'<link rel="manifest"[^>]*>\s*', "", head)
    return (head + f'\n<script>window.KIT = {json.dumps({"name": APP_NAME, "version": VERSION})};</script>'
            '\n<script src="/studio.js"></script>\n<script src="/kit.js"></script>\n</body>\n</html>\n')


def studio_js():
    # les messages du Studio parlent de « Jarvis » : dans le kit, c'est le nom de l'application
    return (CODE / "jarvis" / "studio.js").read_text(encoding="utf-8").replace("Jarvis", APP_NAME)


# ------------------------------------------------------------------ serveur --
state = {"server": None, "relaunch": False}


def relaunch():
    state["relaunch"] = True
    threading.Timer(1.0, state["server"].shutdown).start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, ctype, code=200):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code=200):
        self._send(json.dumps(data, ensure_ascii=False), "application/json; charset=utf-8", code)

    def _body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")

    def do_GET(self):
        last_ping[0] = time.time()
        path = self.path.split("?")[0]
        try:
            if path == "/":
                self._send(page(), "text/html; charset=utf-8")
            elif path == "/studio.js":
                self._send(studio_js(), "text/javascript; charset=utf-8")
            elif path == "/kit.js":
                self._send((HERE / "kit.js").read_bytes(), "text/javascript; charset=utf-8")
            elif path in ("/studio.css", "/inpaint.js"):
                self._send((CODE / "jarvis" / path[1:]).read_bytes(),
                           "text/css; charset=utf-8" if path.endswith(".css") else "text/javascript; charset=utf-8")
            elif path == "/licence":
                self._json(licence.status())
            elif path == "/ping":
                self._json({"ok": True, "version": VERSION, "pid": os.getpid()})
            elif path == "/photo_folders":
                self._json(batch.folders(roots()))
            elif path == "/photo_watch":
                self._json(batch.watch_list(config.load()))
            elif path == "/batch_status":
                self._json(batch.status())
            elif path == "/ai_status":
                self._json(ai_inpaint.status())
            elif path == "/images":
                self._json(recent_images())
            elif path == "/file":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                p = allowed_image(q.get("path", [""])[0])
                if not p:
                    return self._json({"error": "fichier non autorisé"}, 403)
                self._send(p.read_bytes(), mimetypes.guess_type(p.name)[0] or "application/octet-stream")
            elif path == "/licences":
                self._send((HERE / "LICENCES.txt").read_text(encoding="utf-8"), "text/plain; charset=utf-8")
            else:
                self._json({"error": "introuvable"}, 404)
        except Exception as e:
            self._json({"error": str(e)}, 400)

    def do_POST(self):
        last_ping[0] = time.time()
        origin = self.headers.get("Origin")   # refuse les requêtes venant d'autres sites ouverts dans le navigateur
        if origin is not None and not re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin):
            return self._json({"error": "origine refusée"}, 403)
        try:
            d = self._body()
            p = self.path
            if p == "/licence/activate":
                return self._json(licence.activate(d.get("key", "")))
            if p == "/licence/deactivate":
                return self._json(licence.deactivate())
            if p not in ("/gpu", "/open_folder") and not licence.status()["allowed"]:
                return self._json({"error": "L'essai gratuit est terminé : active ta licence (bouton Options) pour continuer."}, 402)
            if p == "/ai_install":
                self._json(ai_inpaint.install(deps_only=bool(d.get("deps_only")), pack=d.get("pack", "lama")))
            elif p == "/ai_upscale":
                with ai_inpaint.user_priority():
                    res = {"image": ai_inpaint.upscale(d.get("image", ""), d.get("factor", 2), d.get("quality", "fast"))}
                self._json(res)
            elif p == "/ai_enhance":
                from jarvis import enhance_ai
                with ai_inpaint.user_priority():
                    res = enhance_ai.enhance_data_url(d.get("image", ""), bool(d.get("best")), bool(d.get("sharp")))
                self._json(res)
            elif p == "/ai_inpaint":
                with ai_inpaint.user_priority():
                    res = {"image": ai_inpaint.inpaint(d.get("image", ""), d.get("mask", ""))}
                self._json(res)
            elif p == "/ai_warmup":
                ai_inpaint.warmup()
                self._json({"ok": True})
            elif p == "/batch_start":
                self._json(batch.start(d.get("folder", ""), bool(d.get("best")), sharp=bool(d.get("sharp"))))
            elif p == "/photo_watch":
                self._json(batch.set_watch(config.load(), d.get("folder", ""), bool(d.get("on", True)),
                                           bool(d.get("best")), bool(d.get("sharp"))))
            elif p == "/batch_cancel":
                self._json(batch.cancel())
            elif p == "/convert_image":
                self._json(batch.to_jpeg_data_url(d.get("image", "")))
            elif p == "/open_folder":
                target = d.get("path") or str(SAVE_DIR)
                system.open_item(str(target))
                self._json({"ok": True})
            elif p == "/scene_cutout":
                from jarvis import scene
                self._json(scene.cutout_data_url(d.get("image", "")))
            elif p == "/scene_background":
                from jarvis import scene
                self._json(scene.background(d.get("prompt", ""), d.get("width", 1024), d.get("height", 1024),
                                            d.get("seed", 1), d.get("mount", "pose")))
            elif p == "/save_image":
                self._json(save_image(d.get("name"), d.get("data"), d.get("fmt"), d.get("quality", 92),
                                      d.get("source_path"), d.get("source_data"), d.get("keep_meta", True),
                                      d.get("keep_gps", False), d.get("download", False)))
            elif p == "/gpu":
                action = d.get("action")
                restart = relaunch
                if batch.job["running"]:   # ne coupe jamais un dossier en cours
                    restart = lambda: batch.on_finish.append(relaunch) if relaunch not in batch.on_finish else None
                if action == "install":
                    gpu.install(on_done=restart)
                elif action in ("on", "off"):
                    gpu.set_enabled(action == "on")
                    restart()
                self._json({"gpu": gpu.info(), "restarting": action in ("install", "on", "off") and not batch.job["running"]})
            else:
                self._json({"error": "introuvable"}, 404)
        except Exception as e:
            self._json({"error": str(e)}, 400)


def open_window(url):
    """Ouvre l'application dans sa propre fenêtre (Edge ou Chrome en mode application), sinon le navigateur."""
    if system.WINDOWS:
        cands = [os.path.expandvars(p) for p in (
            r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe", r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
            r"%ProgramFiles%\Google\Chrome\Application\chrome.exe", r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")]
        for exe in cands:
            if os.path.exists(exe):
                subprocess.Popen([exe, f"--app={url}", "--window-size=1400,900"])
                return
    import webbrowser
    webbrowser.open(url)


def idle_watch():
    """Ferme l'application quand sa fenêtre est fermée (plus aucun signe de vie) et qu'aucun dossier ne tourne."""
    while True:
        time.sleep(30)
        if time.time() - last_ping[0] > 120 and not batch.job["running"] and not batch.queue:
            state["server"].shutdown()
            return


def main():
    url = f"http://127.0.0.1:{PORT}/"
    ThreadingHTTPServer.allow_reuse_address = not system.WINDOWS
    try:
        state["server"] = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        open_window(url)   # déjà ouverte : on montre simplement la fenêtre
        return
    batch.start_watcher(config.load())
    threading.Thread(target=lambda: gpu.available() and ai_inpaint._deps_ok() and gpu.selftest(ai_inpaint.UPSCALE_MODEL),
                     daemon=True).start()
    threading.Thread(target=idle_watch, daemon=True).start()
    threading.Thread(target=licence.recheck, daemon=True).start()
    if "--no-window" not in sys.argv:
        threading.Timer(0.6, lambda: open_window(url)).start()
    print(f"{APP_NAME} {VERSION} : {url}")
    state["server"].serve_forever()
    state["server"].server_close()
    if state["relaunch"]:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--no-window"], creationflags=flags)
    os._exit(0)


if __name__ == "__main__":
    main()

"""Interface web locale : http://localhost:7860 (accessible uniquement depuis ce PC)."""

import base64
import json
import re
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config, system
from .core import Agent, Brain

INDEX = Path(__file__).with_name("index.html")


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
    def __init__(self, cfg, workdir):
        self.cfg, self.ui = cfg, WebUI()
        self.brain = Brain(cfg, self.ui)
        self.workdir = workdir
        self.agent = Agent(self.brain, self.ui, cfg, workdir, auto=cfg["auto"])
        self.busy = False

    def state(self):
        return {"provider": self.brain.name, "model": self.brain.llm.model, "auto": self.agent.tools.auto,
                "busy": self.busy, "workdir": str(self.agent.tools.workdir),
                "providers": {n: config.available(self.cfg, n) for n in self.cfg["providers"]}}

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

        def work():
            self.busy = True
            try:
                self.agent.run(text)
            except Exception as e:
                self.ui.info(f"Erreur : {e}", "error")
                self.ui.done("")
            finally:
                self.busy = False
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
        elif cmd == "key":
            name, key = arg.get("provider"), arg.get("key", "").strip()
            self.cfg["api_keys"][name] = key
            config.save(self.cfg)
        elif cmd == "listen":
            text, err = system.listen()
            return {"text": text, "error": err}
        return self.state()


def serve(cfg, workdir, port=7860, open_browser=True):
    app = App(cfg, workdir)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, data, code=200):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")

        def _local(self):
            # protège contre les requêtes venues d'autres sites ouverts dans le navigateur
            origin = self.headers.get("Origin")
            return origin is None or re.match(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$", origin)

        def do_GET(self):
            if self.path == "/":
                body = INDEX.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/state":
                self._json(app.state())
            elif self.path.startswith("/events"):
                m = re.search(r"since=(\d+)", self.path)
                self._json(app.ui.since(int(m.group(1)) if m else 0))
            else:
                self._json({"error": "introuvable"}, 404)

        def do_POST(self):
            if not self._local():
                return self._json({"error": "origine refusée"}, 403)
            data = self._body()
            try:
                if self.path == "/send":
                    self._json(app.send(data.get("text", ""), data.get("images", [])))
                elif self.path == "/confirm":
                    app.ui.answer(data["id"], "always" if data.get("always") else bool(data.get("ok")))
                    self._json({"ok": True})
                elif self.path == "/command":
                    self._json(app.command(data.get("cmd"), data.get("arg")))
                else:
                    self._json({"error": "introuvable"}, 404)
            except Exception as e:
                self._json({"error": str(e)}, 400)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}"
    print(f"Jarvis est prêt sur {url}  (ferme cette fenêtre pour l'arrêter)")
    if open_browser:
        threading.Timer(1, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

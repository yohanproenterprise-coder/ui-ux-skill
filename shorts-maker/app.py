import re
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

import core

app = Flask(__name__)
jobs: dict[str, dict] = {}


def run(job_id, url, n, length, mode, captions):
    job = jobs[job_id]
    try:
        job["moments"] = core.process(url, n, length, mode, captions, log=lambda m: job.update(status=m))
        job["done"] = True
    except Exception as e:
        job.update(error=re.sub(r'\x1b\[[0-9;]*m', '', str(e)), done=True)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/start")
def start():
    d = request.get_json()
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {"status": "En file…", "done": False}
    threading.Thread(target=run, daemon=True, args=(
        job_id, d["url"], int(d.get("n", 5)), int(d.get("length", 35)),
        d.get("mode", "blur"), bool(d.get("captions", True)))).start()
    return jsonify(id=job_id)


@app.get("/api/job/<job_id>")
def job(job_id):
    return jsonify(jobs.get(job_id, {"error": "inconnu", "done": True}))


@app.get("/clips/<path:p>")
def clips(p):
    return send_from_directory(Path(core.WORK).resolve() / "clips", p)


if __name__ == "__main__":
    app.run(port=5000)

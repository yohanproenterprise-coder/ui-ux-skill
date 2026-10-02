"""Mise à jour de Jarvis depuis GitHub (les réglages, la mémoire et les clés sont conservés)."""

import io
import shutil
import urllib.request
import zipfile
from pathlib import Path

ZIP_URL = ("https://github.com/yohanproenterprise-coder/ui-ux-skill/archive/refs/heads/"
           "claude/quirky-euler-dtsd45.zip")
APP_DIR = Path(__file__).resolve().parent.parent


def update():
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "Jarvis-updater"})
    with urllib.request.urlopen(req, timeout=120) as r:
        archive = zipfile.ZipFile(io.BytesIO(r.read()))
    prefix = next(n for n in archive.namelist() if n.endswith("/local-agent/"))
    count = 0
    for name in archive.namelist():
        if not name.startswith(prefix) or name.endswith("/"):
            continue
        target = APP_DIR / name[len(prefix):]
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(name) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        count += 1
    return f"Mise à jour installée ({count} fichiers). Ferme et relance Jarvis pour l'utiliser."

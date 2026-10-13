"""Mise à jour de Jarvis depuis GitHub (les réglages, la mémoire et les clés sont conservés)."""

import io
import shutil
import urllib.request
import zipfile
from pathlib import Path

ZIP_URL = ("https://github.com/yohanproenterprise-coder/ui-ux-skill/archive/refs/heads/"
           "claude/quirky-euler-dtsd45.zip")
APP_DIR = Path(__file__).resolve().parent.parent


def _home():
    import os
    return Path(os.environ.get("JARVIS_HOME", Path.home() / ".jarvis"))


STAGE = _home() / "maj-en-attente"   # mise à jour téléchargée, appliquée au prochain démarrage


def update(stage=False):
    """Télécharge la dernière version. stage=True : la garde de côté (appliquée au prochain redémarrage),
    pour ne pas changer les fichiers d'un Jarvis en plein travail."""
    req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "Jarvis-updater"})
    with urllib.request.urlopen(req, timeout=120) as r:
        archive = zipfile.ZipFile(io.BytesIO(r.read()))
    prefix = next(n for n in archive.namelist() if n.endswith("/local-agent/"))
    dest_root = STAGE if stage else APP_DIR
    if stage:
        shutil.rmtree(STAGE, ignore_errors=True)
    count = 0
    for name in archive.namelist():
        if not name.startswith(prefix) or name.endswith("/"):
            continue
        target = dest_root / name[len(prefix):]
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(name) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        count += 1
    if stage:
        (STAGE / ".complet").write_text("ok")
        return f"Mise à jour téléchargée ({count} fichiers)."
    shutil.rmtree(STAGE, ignore_errors=True)   # une mise à jour en attente plus ancienne n'a plus lieu d'être
    return f"Mise à jour installée ({count} fichiers). Ferme et relance Jarvis pour l'utiliser."


def pending():
    return (STAGE / ".complet").exists()


def apply_staged():
    """Installe la mise à jour mise de côté (appelé au démarrage, avant de charger le reste de Jarvis)."""
    if not pending():
        return False
    for f in STAGE.rglob("*"):
        if f.is_file() and f.name != ".complet":
            target = APP_DIR / f.relative_to(STAGE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, target)
    shutil.rmtree(STAGE, ignore_errors=True)
    return True

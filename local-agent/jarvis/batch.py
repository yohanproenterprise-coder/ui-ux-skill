"""Amélioration automatique de tout un dossier de photos, en arrière-plan."""

import threading
import time
from pathlib import Path

from . import enhance_ai, photo_export, system

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
OUT_NAME = "Améliorées"
job = {"running": False, "folder": "", "out": "", "total": 0, "done": 0, "current": "", "errors": [],
       "started": 0.0, "finished": 0.0, "cancel": False}
_lock = threading.Lock()


def photos_in(folder):
    return sorted(p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in IMG_EXT)


def status():
    s = dict(job)
    if job["running"] and job["done"]:
        per = (time.time() - job["started"]) / job["done"]
        s["eta"] = int(per * (job["total"] - job["done"]))
    return s


def cancel():
    job["cancel"] = True
    return status()


def start(folder, best=False):
    folder = Path(folder).expanduser()
    if not folder.is_dir():
        raise ValueError(f"Dossier introuvable : {folder}")
    with _lock:
        if job["running"]:
            raise RuntimeError("Une amélioration de dossier est déjà en cours.")
        files = photos_in(folder)
        if not files:
            raise ValueError("Aucune photo dans ce dossier.")
        out = folder / OUT_NAME
        job.update(running=True, folder=str(folder), out=str(out), total=len(files), done=0, current="",
                   errors=[], started=time.time(), finished=0.0, cancel=False)

    def work():
        from PIL import Image, ImageOps
        out.mkdir(exist_ok=True)
        try:
            for f in files:
                if job["cancel"]:
                    break
                job["current"] = f.name
                try:
                    img = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
                    better, _ = enhance_ai.enhance(img, best)
                    fmt = "png" if f.suffix.lower() == ".png" else "jpeg"
                    raw, ext = photo_export.encode_image(better, fmt, 92, source_path=str(f), keep_meta=True, keep_gps=True)
                    (out / f"{f.stem}.{ext}").write_bytes(raw)  # l'original n'est jamais modifié
                except Exception as e:
                    job["errors"].append(f"{f.name} : {e}")
                job["done"] += 1
        finally:
            job.update(running=False, current="", finished=time.time())
            n = job["done"] - len(job["errors"])
            msg = (f"Arrêté : {n} photo(s) améliorée(s)" if job["cancel"] else f"{n} photo(s) améliorée(s)") + f" dans {out}"
            try:
                system.notify("Jarvis — photos améliorées", msg)
            except Exception:
                pass
    threading.Thread(target=work, daemon=True).start()
    return status()


def folders(roots, limit=40):
    """Dossiers qui contiennent des photos (pour choisir facilement), les plus récents d'abord."""
    import os
    found = []
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            dirnames[:] = [] if depth >= 3 else [d for d in dirnames if not d.startswith((".", "$")) and d not in (OUT_NAME, "node_modules")]
            n = sum(1 for x in filenames if Path(x).suffix.lower() in IMG_EXT)
            if n:
                try:
                    found.append((os.path.getmtime(dirpath), dirpath, n))
                except OSError:
                    pass
    found.sort(reverse=True)
    seen, out = set(), []
    for _, d, n in found:
        if d not in seen:
            seen.add(d)
            out.append({"path": d, "name": Path(d).name, "count": n})
    return out[:limit]

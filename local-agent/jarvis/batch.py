"""Amélioration automatique de tout un dossier de photos, en arrière-plan."""

import threading
import time
from pathlib import Path

from . import enhance_ai, photo_export, system

IMG_EXT = {".jpg", ".jpeg", ".jfif", ".png", ".webp", ".bmp", ".tif", ".tiff", ".avif", ".heic", ".heif"}
OUT_NAME = "Améliorées"
job = {"running": False, "folder": "", "out": "", "total": 0, "done": 0, "current": "", "errors": [],
       "started": 0.0, "finished": 0.0, "cancel": False}
_lock = threading.Lock()


def _register_formats():
    """HEIC/AVIF (iPhone, Shopify…) : lus grâce à pillow-heif s'il est installé (installé automatiquement si besoin)."""
    try:
        import pillow_heif
    except ImportError:
        try:
            from .ai_inpaint import _pip
            _pip(["pillow-heif"])
            import pillow_heif
        except Exception:
            return
    for fn in ("register_heif_opener", "register_avif_opener"):
        try:
            getattr(pillow_heif, fn)()
        except Exception:
            pass


def to_jpeg_data_url(data_url):
    """Convertit une photo que le navigateur ne sait pas lire (HEIC, AVIF…) en JPEG pour le Studio."""
    import base64
    import io
    from PIL import Image, ImageOps
    _register_formats()
    raw = base64.b64decode(data_url.split(",", 1)[1])
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95, subsampling=0)
    return {"image": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}


def clean_path(folder):
    """Chemin collé tel quel : guillemets de « Copier en tant que chemin », espaces, fichier au lieu du dossier."""
    s = str(folder or "").strip().strip('"\'').strip()
    if s.lower().startswith("file:///"):
        from urllib.parse import unquote
        s = unquote(s[8:])
    p = Path(s).expanduser()
    if p.is_file():
        p = p.parent
    return p


def photos_in(folder):
    """Photos du dossier et de ses sous-dossiers (sauf « Améliorées »)."""
    folder = Path(folder)
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXT
                  and OUT_NAME not in p.relative_to(folder).parts)


def status():
    s = dict(job)
    if job["running"]:  # avancement de la photo en cours (l'IA peut prendre du temps sur une grande photo)
        up = enhance_ai.ai_inpaint.upscale_state
        p = int(up.get("progress") or 0) if up.get("busy") or up.get("step") else 0
        # le nettoyage par IA (0 à 100 %) représente environ les 3/4 du travail sur une photo
        s["photo_progress"] = int(p * .72) if (up.get("step") or "").startswith("Nettoyage") else p
        s["photo_step"] = up.get("step") or ""
    if job["running"] and job["done"]:
        per = (time.time() - job["started"]) / job["done"]
        s["eta"] = int(per * (job["total"] - job["done"]))
    return s


def cancel():
    job["cancel"] = True
    return status()


def _target(folder, out, f):
    """Fichier amélioré correspondant à la photo f (même sous-dossier, même nom)."""
    dest = out / f.parent.relative_to(folder) if f.parent != folder else out
    return dest / f"{f.stem}.{'png' if f.suffix.lower() == '.png' else 'jpg'}"


_failed = set()   # photos en échec (chemin, date) : la surveillance ne les réessaie pas en boucle


def start(folder, best=False, only_new=False):
    """Lance l'amélioration du dossier. only_new : seulement les photos pas encore améliorées (surveillance)."""
    folder = clean_path(folder)
    if not folder.is_dir():
        raise ValueError(f"Dossier introuvable : {folder}. Astuce : dans l'explorateur, clic droit sur le dossier → "
                         "« Copier en tant que chemin d'accès », puis colle-le ici.")
    with _lock:
        if job["running"]:
            raise RuntimeError("Une amélioration de dossier est déjà en cours.")
        files = photos_in(folder)
        out = folder / OUT_NAME
        if only_new:
            now = time.time()
            files = [f for f in files if not _target(folder, out, f).exists() and (str(f), f.stat().st_mtime) not in _failed
                     and now - f.stat().st_mtime > 8]   # photo encore en cours de copie : on attend
            if not files:
                return None
        if not files:
            others = sorted({p.suffix.lower() or p.name for p in folder.rglob("*") if p.is_file()})[:8]
            raise ValueError("Aucune photo dans ce dossier" + (f" (fichiers trouvés : {', '.join(others)})" if others else " (il est vide)")
                             + ". Formats acceptés : JPG, PNG, WEBP, AVIF, HEIC, TIFF, BMP.")
        job.update(running=True, folder=str(folder), out=str(out), total=len(files), done=0, current="",
                   errors=[], started=time.time(), finished=0.0, cancel=False)

    def work():
        from PIL import Image, ImageOps
        out.mkdir(exist_ok=True)
        if any(f.suffix.lower() in (".avif", ".heic", ".heif") for f in files):
            _register_formats()
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
                    target = _target(folder, out, f)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)  # l'original n'est jamais modifié
                except Exception as e:
                    job["errors"].append(f"{f.name} : {e}")
                    try:
                        _failed.add((str(f), f.stat().st_mtime))
                    except OSError:
                        pass
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


# ------------------------------------------------------------ surveillance --
def watch_list(cfg):
    return list(cfg.get("photo_watch") or [])


def set_watch(cfg, folder, on=True, best=False):
    """Ajoute ou retire un dossier surveillé (les nouvelles photos y sont améliorées automatiquement)."""
    from . import config
    folder = clean_path(folder)
    lst = [w for w in watch_list(cfg) if Path(w["folder"]) != folder]
    if on:
        if not folder.is_dir():
            raise ValueError(f"Dossier introuvable : {folder}")
        lst.append({"folder": str(folder), "best": bool(best)})
    cfg["photo_watch"] = lst
    config.save(cfg)
    return lst


def start_watcher(cfg, every=30):
    """Vérifie régulièrement les dossiers surveillés et améliore les nouvelles photos, en arrière-plan."""
    def loop():
        time.sleep(15)
        while True:
            for w in watch_list(cfg):
                if job["running"]:
                    break
                try:
                    if Path(w["folder"]).is_dir() and enhance_ai.ai_inpaint._deps_ok():
                        start(w["folder"], w.get("best", False), only_new=True)
                except Exception:
                    pass
            time.sleep(every)
    threading.Thread(target=loop, daemon=True, name="photo-watch").start()


def folders(roots, limit=40):
    """Dossiers qui contiennent des photos (y compris dans leurs sous-dossiers), les plus récents d'abord."""
    import os
    found = {}
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            dirnames[:] = [] if depth >= 4 else [d for d in dirnames if not d.startswith((".", "$")) and d not in (OUT_NAME, "node_modules")]
            n = sum(1 for x in filenames if Path(x).suffix.lower() in IMG_EXT)
            if not n:
                continue
            try:
                t = os.path.getmtime(dirpath)
            except OSError:
                continue
            d = Path(dirpath)
            while True:  # le dossier et ses parents (ex. « NEW PHOTO SHOPIFY\AEVYX » si les photos sont rangées dedans)
                t0, n0 = found.get(str(d), (0, 0))
                found[str(d)] = (max(t0, t), n0 + n)
                if d == root or d.parent == d or len(d.relative_to(root).parts) <= 1:
                    break
                d = d.parent
    out = [{"path": d, "name": " › ".join(Path(d).parts[-2:]), "count": n}
           for d, (t, n) in sorted(found.items(), key=lambda kv: -kv[1][0])]
    return out[:limit]

"""IA de retouche (LaMa) : efface une zone et la reconstruit de façon réaliste.

Tourne sur le PC avec onnxruntime. Le modèle (≈ 92 Mo) et les bibliothèques sont installés
une seule fois, à la demande, depuis le Studio.
"""

import base64
import importlib
import io
import os
import site
import subprocess
import sys
import threading
import time
import urllib.request

from .config import HOME

MODEL = HOME / "models" / "lama.onnx"
UPSCALE_MODEL = __import__("pathlib").Path(__file__).resolve().parent / "models" / "upscale-x4.onnx"
MODEL_URLS = [  # LaMa (Carve / OpenCV Zoo, licence Apache 2.0)
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/inpainting_lama/inpainting_lama_2025jan.onnx",
    "https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx",
]
FF = "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/"
MODELS = HOME / "models"
# paquets d'IA téléchargeables : (adresses possibles, fichier, taille minimale)
PACKS = {
    "lama": [(MODEL_URLS, MODEL, 50_000_000)],
    "faces": [([FF + "yoloface_8n.onnx"], MODELS / "yoloface_8n.onnx", 10_000_000),
              ([FF + "codeformer.onnx"], MODELS / "codeformer.onnx", 300_000_000)],
    "upmax": [([FF + "real_esrgan_x2.onnx"], MODELS / "real_esrgan_x2.onnx", 60_000_000)],
}
PACKS["enhance"] = PACKS["faces"] + PACKS["upmax"]  # tout ce qu'utilise l'amélioration en un clic
PACK_LABELS = {"enhance": "IA d'amélioration (≈ 460 Mo)","lama": "IA de retouche (≈ 92 Mo)", "faces": "IA des visages (≈ 390 Mo)",
               "upmax": "agrandissement Qualité max (≈ 70 Mo)"}
SIZE = 512
state = {"state": "absent", "step": "", "progress": 0, "error": ""}
upscale_state = {"busy": False, "progress": 0}
_session, _last_use, _lock = None, 0.0, threading.Lock()
_up_session = None


def _deps_ok():
    try:
        import numpy  # noqa: F401
        import onnxruntime  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def pack_ready(name):
    return all(f.exists() and f.stat().st_size > mn for _, f, mn in PACKS[name])


def status():
    extra = {"deps": _deps_ok(), "upscale": dict(upscale_state),
             "packs": {k: pack_ready(k) for k in PACKS}}
    if state["state"] in ("installing", "error"):
        return {**state, **extra}
    ready = MODEL.exists() and MODEL.stat().st_size > 50_000_000 and extra["deps"]
    state.update(state="ready" if ready else "absent")
    return {**state, **extra}


def _pip(packages):
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "--disable-pip-version-check",
                        *packages], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("installation impossible : " + (r.stderr or r.stdout)[-300:])
    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.append(user_site)
    importlib.invalidate_caches()


def _download_pack(name):
    files = [(urls, f, mn) for urls, f, mn in PACKS[name] if not (f.exists() and f.stat().st_size > mn)]
    for n, (urls, dest, minsize) in enumerate(files, 1):
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp, last_err = dest.with_suffix(".part"), None
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Jarvis"})
                with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                    total, done = int(r.headers.get("Content-Length") or 0), 0
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        state["progress"] = int(100 * done / total) if total else min(99, done // 1_000_000)
                        state["step"] = f"Téléchargement {PACK_LABELS[name]} — fichier {n}/{len(files)}…"
                if tmp.stat().st_size < minsize:
                    raise RuntimeError("fichier incomplet")
                os.replace(tmp, dest)
                break
            except Exception as e:
                last_err = e
        else:
            raise RuntimeError(f"téléchargement impossible ({last_err}). Vérifie ta connexion et réessaie.")


def install(deps_only=False, pack="lama"):
    """Lance l'installation en arrière-plan ; suivre l'avancement avec status()."""
    pack = pack if pack in PACKS else "lama"
    if state["state"] == "installing":
        return status()

    def work():
        try:
            state.update(state="installing", error="", progress=0, step="Installation des bibliothèques (≈ 20 Mo)…")
            if not _deps_ok():
                _pip(["onnxruntime", "numpy", "pillow"])
            try:
                import onnxruntime  # noqa: F401
            except ImportError as e:
                hint = (" Installe le composant Microsoft « Visual C++ Redistributable » : "
                        "https://aka.ms/vs/17/release/vc_redist.x64.exe puis réessaie.") if "DLL" in str(e) else ""
                raise RuntimeError(f"le moteur d'IA ne démarre pas ({e}).{hint}")
            if deps_only:
                state.update(state="absent", step="", progress=100)
                return
            state.update(progress=0)
            _download_pack(pack)
            state.update(step="Vérification…", progress=100)
            if pack == "lama":
                _get_session()
            state.update(state="absent", step="Prêt")
            status()
        except Exception as e:
            state.update(state="error", error=str(e), step="")
    threading.Thread(target=work, daemon=True).start()
    time.sleep(0.2)
    return status()


def _get_session():
    global _session, _last_use
    with _lock:
        if _session is None:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            _session = ort.InferenceSession(str(MODEL), sess_options=opts, providers=["CPUExecutionProvider"])
            threading.Thread(target=_unload_when_idle, daemon=True).start()
        _last_use = time.time()
        return _session


def _unload_when_idle():
    # libère la mémoire (≈ 1 Go) après 10 minutes sans retouche
    global _session
    while True:
        time.sleep(60)
        with _lock:
            if _session is not None and time.time() - _last_use > 600:
                _session = None
                return


def _decode(data_url, mode):
    from PIL import Image
    raw = base64.b64decode(data_url.split(",", 1)[1])
    return Image.open(io.BytesIO(raw)).convert(mode)


def inpaint(image_data_url, mask_data_url):
    """Reçoit la zone de la photo et son masque (blanc = à effacer), renvoie la zone reconstruite."""
    import numpy as np
    from PIL import Image
    if status()["state"] != "ready":
        raise RuntimeError("L'IA de retouche n'est pas installée (bouton « Installer l'IA » dans le Studio).")
    img, mask = _decode(image_data_url, "RGB"), _decode(mask_data_url, "L")
    w, h = img.size
    side = max(w, h)
    # carré par recopie des bords, pour ne pas déformer la photo
    a = np.pad(np.asarray(img), ((0, side - h), (0, side - w), (0, 0)), mode="edge")
    m = np.pad(np.asarray(mask), ((0, side - h), (0, side - w)))
    x = np.asarray(Image.fromarray(a).resize((SIZE, SIZE), Image.BICUBIC), dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    mk = (np.asarray(Image.fromarray(m).resize((SIZE, SIZE), Image.NEAREST)) > 127).astype(np.float32)[None, None]
    out = _get_session().run(None, {"image": x, "mask": mk})[0][0].transpose(1, 2, 0)
    if out.max() <= 2:
        out = out * 255
    res = Image.fromarray(out.clip(0, 255).astype(np.uint8)).resize((side, side), Image.LANCZOS).crop((0, 0, w, h))
    buf = io.BytesIO()
    res.save(buf, "PNG", compress_level=1)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------ agrandissement --

def _tiled(src, run, scale, tile, pad, progress=(0, 100), even=False):
    """Exécute run() tuile par tuile avec des bords qui se chevauchent et un fondu progressif
    (aucune couture visible entre les tuiles). src : tableau HxWx3 dans [0,1]."""
    import numpy as np
    h, w = src.shape[:2]
    acc = np.zeros((h * scale, w * scale, 3), np.float32)
    wsum = np.zeros((h * scale, w * scale, 1), np.float32)
    step = tile
    tiles = [(x, y) for y in range(0, h, step) for x in range(0, w, step)]
    for n, (x, y) in enumerate(tiles):
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(w, x + step + pad), min(h, y + step + pad)
        part = src[y0:y1, x0:x1]
        ph, pw = part.shape[:2]
        if even:
            part = np.pad(part, ((0, ph % 2), (0, pw % 2), (0, 0)), mode="edge")
        res = run(part)[:ph * scale, :pw * scale]
        # poids : 1 au centre, descend doucement vers les bords qui chevauchent une autre tuile
        ramp = pad * scale
        wy = np.ones(ph * scale, np.float32)
        wx = np.ones(pw * scale, np.float32)
        if ramp > 0:
            r = np.linspace(0.05, 1, ramp, dtype=np.float32)
            if y0 > 0:
                wy[:ramp] = r[:len(wy[:ramp])]
            if y1 < h:
                wy[-ramp:] = np.minimum(wy[-ramp:], r[::-1][-len(wy[-ramp:]):])
            if x0 > 0:
                wx[:ramp] = r[:len(wx[:ramp])]
            if x1 < w:
                wx[-ramp:] = np.minimum(wx[-ramp:], r[::-1][-len(wx[-ramp:]):])
        wgt = (wy[:, None] * wx[None, :])[..., None]
        acc[y0 * scale:y1 * scale, x0 * scale:x1 * scale] += res * wgt
        wsum[y0 * scale:y1 * scale, x0 * scale:x1 * scale] += wgt
        upscale_state["progress"] = int(progress[0] + (progress[1] - progress[0]) * (n + 1) / len(tiles))
    return acc / np.maximum(wsum, 1e-6)

_max_session = None


def _max_x2(img, tile=320, pad=20, progress=(0, 100)):
    """Agrandissement ×2 « Qualité max » (Real-ESRGAN complet), par tuiles de taille paire."""
    global _max_session
    import numpy as np
    from PIL import Image
    if _max_session is None:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        _max_session = ort.InferenceSession(str(MODELS / "real_esrgan_x2.onnx"), sess_options=opts,
                                            providers=["CPUExecutionProvider"])
    src = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    run = lambda part: _max_session.run(None, {"input": part.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
    out = _tiled(src, run, 2, tile, pad, progress, even=True)
    return Image.fromarray((out.clip(0, 1) * 255).round().astype(np.uint8))


def upscale_image(img, factor=2, tile=384, pad=16, quality="fast"):
    """Agrandit une image PIL ×2 ou ×4 avec Real-ESRGAN (rendu naturel), par tuiles pour limiter la mémoire."""
    global _up_session
    import numpy as np
    from PIL import Image
    if not _deps_ok():
        raise RuntimeError("L'IA n'est pas installée (bouton « Installer l'IA » dans le Studio).")
    factor = 4 if int(factor) >= 4 else 2
    w, h = img.size
    if max(w, h) * factor > 8000:
        raise RuntimeError(f"Image trop grande pour ×{factor} (résultat limité à 8000 px). Réduis-la d'abord ou choisis ×2.")
    if quality == "max" and pack_ready("upmax"):
        upscale_state.update(busy=True, progress=0)
        try:
            res = _max_x2(img, progress=(0, 100 if factor == 2 else 50))
            if factor == 4:
                res = _max_x2(res, progress=(50, 100))
        finally:
            upscale_state["busy"] = False
        # 25 % d'agrandissement classique : grain réel conservé
        return Image.blend(res, img.convert("RGB").resize(res.size, Image.LANCZOS), 0.25)
    if _up_session is None:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        _up_session = ort.InferenceSession(str(UPSCALE_MODEL), sess_options=opts, providers=["CPUExecutionProvider"])
    src = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    upscale_state.update(busy=True, progress=0)
    try:
        run = lambda part: _up_session.run(None, {"input": part.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
        out4 = _tiled(src, run, 4, tile, pad)
        res = Image.fromarray((out4.clip(0, 1) * 255).round().astype(np.uint8))
        if factor != 4:  # ×4 puis réduction soignée : plus net qu'un ×2 direct
            res = res.resize((w * factor, h * factor), Image.LANCZOS)
        out = np.asarray(res)
    finally:
        upscale_state["busy"] = False
    # 35 % d'agrandissement classique : garde le grain réel (peau, matières) pour un rendu naturel
    res = Image.fromarray(out)
    return Image.blend(res, img.convert("RGB").resize(res.size, Image.LANCZOS), 0.35)


def upscale(image_data_url, factor=2, quality="fast"):
    img = _decode(image_data_url, "RGB")
    res = upscale_image(img, factor, quality=quality)
    buf = io.BytesIO()
    res.save(buf, "PNG", compress_level=1)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------------- visages --
def restore_faces(image_data_url, strength=0.8):
    from . import ai_face
    if not (_deps_ok() and pack_ready("faces")):
        raise RuntimeError("L'IA des visages n'est pas installée.")
    upscale_state.update(busy=True, progress=10)
    try:
        img, n = ai_face.restore(_decode(image_data_url, "RGB"), strength=float(strength), fidelity=1.0)
    finally:
        upscale_state.update(busy=False, progress=100)
    buf = io.BytesIO()
    img.save(buf, "PNG", compress_level=1)
    return {"image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), "faces": n}


def warmup():
    """Charge les IA en mémoire en arrière-plan (évite 20 à 40 s d'attente au premier clic)."""
    def work():
        global _up_session, _max_session
        try:
            if not _deps_ok():
                return
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            if _up_session is None:
                _up_session = ort.InferenceSession(str(UPSCALE_MODEL), sess_options=opts, providers=["CPUExecutionProvider"])
            if pack_ready("faces"):
                from . import ai_face
                ai_face._session(ai_face.DETECTOR[0])
                ai_face._session(ai_face.RESTORER[0])
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()

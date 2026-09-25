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


def status():
    extra = {"deps": _deps_ok(), "upscale": dict(upscale_state)}
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


def _download():
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    tmp = MODEL.with_suffix(".part")
    last_err = None
    for url in MODEL_URLS:
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
            if tmp.stat().st_size < 50_000_000:
                raise RuntimeError("fichier incomplet")
            os.replace(tmp, MODEL)
            return
        except Exception as e:
            last_err = e
    raise RuntimeError(f"téléchargement du modèle impossible ({last_err})")


def install(deps_only=False):
    """Lance l'installation en arrière-plan ; suivre l'avancement avec status()."""
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
            if not (MODEL.exists() and MODEL.stat().st_size > 50_000_000):
                state.update(step="Téléchargement du modèle d'IA (≈ 92 Mo)…", progress=0)
                _download()
            state.update(step="Vérification…", progress=100)
            _get_session()
            state.update(state="ready", step="Prêt")
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
            opts.intra_op_num_threads = max(1, os.cpu_count() or 1)
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
    res.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------ agrandissement --
def upscale_image(img, factor=2, tile=256, pad=12):
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
    if _up_session is None:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = max(1, os.cpu_count() or 1)
        opts.log_severity_level = 3
        _up_session = ort.InferenceSession(str(UPSCALE_MODEL), sess_options=opts, providers=["CPUExecutionProvider"])
    src = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    out = np.zeros((h * factor, w * factor, 3), dtype=np.uint8)
    tiles = [(x, y) for y in range(0, h, tile) for x in range(0, w, tile)]
    upscale_state.update(busy=True, progress=0)
    try:
        for n, (x, y) in enumerate(tiles):
            x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(w, x + tile + pad), min(h, y + tile + pad)
            inp = src[y0:y1, x0:x1].transpose(2, 0, 1)[None]
            res = _up_session.run(None, {"input": inp})[0][0].transpose(1, 2, 0)
            res = Image.fromarray((res.clip(0, 1) * 255).round().astype(np.uint8))
            if factor != 4:  # ×4 puis réduction soignée : plus net qu'un ×2 direct
                res = res.resize(((x1 - x0) * factor, (y1 - y0) * factor), Image.LANCZOS)
            res = np.asarray(res)
            cx0, cy0 = (x - x0) * factor, (y - y0) * factor
            cw, ch = (min(w, x + tile) - x) * factor, (min(h, y + tile) - y) * factor
            out[y * factor:y * factor + ch, x * factor:x * factor + cw] = res[cy0:cy0 + ch, cx0:cx0 + cw]
            upscale_state["progress"] = int(100 * (n + 1) / len(tiles))
    finally:
        upscale_state["busy"] = False
    # 35 % d'agrandissement classique : garde le grain réel (peau, matières) pour un rendu naturel
    res = Image.fromarray(out)
    return Image.blend(res, img.convert("RGB").resize(res.size, Image.LANCZOS), 0.35)


def upscale(image_data_url, factor=2):
    img = _decode(image_data_url, "RGB")
    res = upscale_image(img, factor)
    buf = io.BytesIO()
    res.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

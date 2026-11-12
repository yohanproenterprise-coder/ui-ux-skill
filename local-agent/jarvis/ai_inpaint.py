"""IA de retouche (LaMa) : efface une zone et la reconstruit de façon réaliste.

Tourne sur le PC avec onnxruntime. Le modèle (≈ 92 Mo) et les bibliothèques sont installés
une seule fois, à la demande, depuis le Studio.
"""

import base64
import importlib
import io
import os
import shutil
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
    "sharp": [([FF + "nomos8k_sc_x4.onnx"], MODELS / "nomos8k_sc_x4.onnx", 60_000_000)],
    # détourage (BiRefNet lite, licence MIT, conversion ONNX du projet rembg)
    "cutout": [(["https://github.com/danielgatis/rembg/releases/download/v0.0.0/"
                 "BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx"], MODELS / "birefnet-lite.onnx", 200_000_000)],
}
# fichiers facultatifs (accélèrent, mais le paquet fonctionne sans) : téléchargés avec le paquet, ou en arrière-plan
OPTIONAL = {"faces": [([FF + "gpen_bfr_256.onnx"], MODELS / "gpen_bfr_256.onnx", 70_000_000)]}
PACKS["enhance"] = PACKS["faces"] + PACKS["upmax"]  # tout ce qu'utilise l'amélioration en un clic
OPTIONAL["enhance"] = OPTIONAL["faces"]
PACK_LABELS = {"enhance": "IA d'amélioration (≈ 530 Mo)","lama": "IA de retouche (≈ 92 Mo)", "faces": "IA des visages (≈ 460 Mo)",
               "upmax": "agrandissement Qualité max (≈ 70 Mo)", "sharp": "IA netteté renforcée (≈ 67 Mo)",
               "cutout": "IA de détourage (≈ 225 Mo)"}
UI_LABELS = {}   # textes d'installation propres à une application (Photo Studio IA), sinon ceux du Studio
SIZE = 512
state = {"state": "absent", "step": "", "progress": 0, "error": ""}
upscale_state = {"busy": False, "progress": 0}               # opérations lancées depuis le Studio
batch_state = {"busy": False, "progress": 0, "step": "", "paused": False}   # amélioration de dossier
_local = threading.local()
_user_ops, _ops_lock, _user_idle = 0, threading.Lock(), threading.Event()
_user_idle.set()


def set_background(on):
    """Le fil courant travaille en arrière-plan (dossier) : il cède la place aux retouches du Studio."""
    _local.background = bool(on)


def ustate():
    """État d'avancement du travail en cours (Studio ou dossier, chacun le sien)."""
    return batch_state if getattr(_local, "background", False) else upscale_state


class user_priority:
    """Pendant une retouche lancée depuis le Studio, l'amélioration de dossier se met en pause."""
    def __enter__(self):
        global _user_ops
        with _ops_lock:
            _user_ops += 1
            _user_idle.clear()

    def __exit__(self, *exc):
        global _user_ops
        with _ops_lock:
            _user_ops -= 1
            if _user_ops <= 0:
                _user_ops = 0
                _user_idle.set()


def yield_to_user():
    """Appelé régulièrement par le travail en arrière-plan : attend la fin des retouches du Studio."""
    if getattr(_local, "background", False) and not _user_idle.is_set():
        batch_state["paused"] = True
        _user_idle.wait()
        batch_state["paused"] = False
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
    from . import gpu
    extra = {"deps": _deps_ok(), "upscale": dict(upscale_state), "gpu": gpu.info(),
             "packs": {k: pack_ready(k) for k in PACKS}, "labels": UI_LABELS}
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


def _download_optional(name):
    """Télécharge sans bruit les fichiers facultatifs d'un paquet déjà installé (ex. visages rapides)."""
    for urls, dest, minsize in OPTIONAL.get(name, []):
        if dest.exists() and dest.stat().st_size > minsize:
            continue
        tmp = dest.with_suffix(".part")
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Jarvis"})
                with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                    shutil.copyfileobj(r, f, 1 << 20)
                if tmp.stat().st_size >= minsize:
                    os.replace(tmp, dest)
                    break
            except Exception:
                pass


def _download_pack(name):
    files = [(urls, f, mn) for urls, f, mn in PACKS[name] + OPTIONAL.get(name, []) if not (f.exists() and f.stat().st_size > mn)]
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


class _Session:
    """Session d'IA sur la carte graphique si elle est active, sinon sur le processeur.
    Chaque modèle est vérifié une fois sur la carte graphique : s'il y est plus lent que sur le processeur,
    trop long à préparer (> 3 min) ou en erreur, il repasse pour de bon sur le processeur (choix mémorisé)."""
    FIRST_TIMEOUT = 180

    def __init__(self, path):
        from . import gpu
        self.path, self.lock = str(path), threading.Lock()
        prov = gpu.providers()
        self.gpu = prov[0] != "CPUExecutionProvider" and gpu.model_choice(path) != "cpu"
        self.checked = gpu.model_choice(path) == "gpu"
        try:
            self.s = self._make(prov if self.gpu else ["CPUExecutionProvider"])
        except Exception:
            self.s, self.gpu = self._make(["CPUExecutionProvider"]), False

    def _make(self, prov):
        import onnxruntime as ort
        o = ort.SessionOptions()
        o.log_severity_level = 3
        if prov[0] != "CPUExecutionProvider":   # exigé par DirectML
            o.enable_mem_pattern = False
            o.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        return ort.InferenceSession(self.path, sess_options=o, providers=prov)

    def get_inputs(self):
        return self.s.get_inputs()

    def _to_cpu(self, reason):
        from . import gpu
        self.s, self.gpu = self._make(["CPUExecutionProvider"]), False
        gpu.set_model_choice(self.path, "cpu", reason)

    def _check(self, *a, **k):
        """Premier passage du modèle sur la carte graphique : préparation surveillée, puis duel avec le processeur."""
        from . import gpu
        st = ustate()
        step = st.get("step", "")
        st["step"] = "Préparation de l'IA sur la carte graphique (1re fois, jusqu'à 3 min)…"
        box = {}

        def first():
            try:
                with self.lock:
                    box["out"] = self.s.run(*a, **k)
            except Exception as e:
                box["err"] = e
        th = threading.Thread(target=first, daemon=True)
        th.start()
        th.join(self.FIRST_TIMEOUT)
        st["step"] = step
        if th.is_alive() or "err" in box:
            self._to_cpu("trop long à préparer" if th.is_alive() else f"erreur : {box['err']}")
            return self.s.run(*a, **k)
        try:
            t = time.time()
            with self.lock:
                self.s.run(*a, **k)
            gpu_t = time.time() - t
            cpu = self._make(["CPUExecutionProvider"])
            t = time.time()
            cpu.run(*a, **k)
            cpu_t = time.time() - t
        except Exception as e:
            self._to_cpu(f"erreur : {e}")
            return self.s.run(*a, **k)
        self.checked = True
        if gpu_t > cpu_t * .9:   # pas plus rapide pour ce modèle : processeur
            self.s, self.gpu = cpu, False
            gpu.set_model_choice(self.path, "cpu", f"plus lent sur la carte graphique ({gpu_t:.1f} s contre {cpu_t:.1f} s)")
        else:
            gpu.set_model_choice(self.path, "gpu", f"×{cpu_t / max(gpu_t, 1e-6):.1f}")
        return box["out"]

    def run(self, *a, **k):
        if not self.gpu:
            return self.s.run(*a, **k)
        if not self.checked:
            return self._check(*a, **k)
        try:
            with self.lock:   # une seule exécution à la fois sur la carte graphique
                return self.s.run(*a, **k)
        except Exception as e:
            self._to_cpu(f"erreur : {e}")
            return self.s.run(*a, **k)


def new_session(path):
    return _Session(path)


def _get_session():
    global _session, _last_use
    with _lock:
        if _session is None:
            _session = new_session(MODEL)
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


def _finish_fill(img, res, mask):
    """Rend la zone reconstruite indiscernable : couleurs raccordées au bord et même grain que la photo."""
    import numpy as np
    from PIL import Image, ImageFilter
    o = np.asarray(img, np.float32)
    r = np.asarray(res, np.float32)
    hole = np.asarray(mask) > 127
    if not hole.any():
        return res
    # anneau juste autour de la zone effacée : ce que l'IA doit prolonger sans décalage de couleur
    big = np.asarray(mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MaxFilter(9))) > 127
    ring = big & ~hole
    if ring.sum() > 50:
        shift = np.clip((o[ring] - r[ring]).mean(0), -10, 10)
        r[hole] += shift
    # grain : on mesure le grain de la photo autour (hautes fréquences) et on complète celui de la zone
    lum = lambda a: a @ np.array([.299, .587, .114], np.float32)
    def hp(a):
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        return lum(a) - lum(np.asarray(im.filter(ImageFilter.GaussianBlur(1.0)), np.float32))
    ho, hr = hp(o), hp(r)
    around = big & ~hole if ring.sum() > 200 else ~hole
    mad = lambda v: 1.4826 * np.median(np.abs(v - np.median(v))) if v.size else 0.0
    want, have = mad(ho[around]), mad(hr[hole])
    extra = np.sqrt(max(0.0, want ** 2 - have ** 2))
    if extra > 0.3:
        rng = np.random.default_rng(7)
        noise = rng.normal(0, extra, hole.sum()).astype(np.float32)
        r[hole] += noise[:, None]
    return Image.fromarray(np.clip(r, 0, 255).astype(np.uint8))


def inpaint(image_data_url, mask_data_url):
    """Reçoit la zone de la photo (jusqu'à 2048 px) et son masque (blanc = à effacer), renvoie la zone reconstruite."""
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
    mk = (np.asarray(Image.fromarray(m).resize((SIZE, SIZE), Image.BILINEAR)) > 20).astype(np.float32)[None, None]
    out = _get_session().run(None, {"image": x, "mask": mk})[0][0].transpose(1, 2, 0)
    if out.max() <= 2:
        out = out * 255
    small = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    if side > SIZE * 1.25:
        # zone plus grande que ce que voit l'IA : ré-affinage par l'IA d'agrandissement (au lieu d'un simple flou d'agrandissement)
        try:
            res = upscale_image(small, 4, quality="fast").resize((side, side), Image.LANCZOS)
        except Exception:
            res = small.resize((side, side), Image.LANCZOS)
    else:
        res = small.resize((side, side), Image.LANCZOS)
    res = _finish_fill(img, res.crop((0, 0, w, h)), mask)
    buf = io.BytesIO()
    res.save(buf, "PNG", compress_level=1)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ------------------------------------------------------------ agrandissement --

def _tiled(src, run, scale, tile, pad, progress=(0, 100), even=False):
    """Exécute run() tuile par tuile avec des bords qui se chevauchent et un fondu progressif
    (aucune couture visible entre les tuiles). src : tableau HxWx3 dans [0,1].
    Les tuiles sont réparties à parts égales (le moins de tuiles possible, de taille ≤ tile)."""
    import math
    import numpy as np
    h, w = src.shape[:2]
    if h <= tile and w <= tile:  # tout tient en une fois : pas de découpe
        part = np.pad(src, ((0, h % 2), (0, w % 2), (0, 0)), mode="edge") if even else src
        ustate()["progress"] = int(progress[1])
        return run(part)[:h * scale, :w * scale]
    nx, ny = math.ceil(w / tile), math.ceil(h / tile)
    sx, sy = math.ceil(w / nx), math.ceil(h / ny)
    acc = np.zeros((h * scale, w * scale, 3), np.float32)
    wsum = np.zeros((h * scale, w * scale, 1), np.float32)
    tiles = [(x, y) for y in range(0, h, sy) for x in range(0, w, sx)]
    for n, (x, y) in enumerate(tiles):
        yield_to_user()
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(w, x + sx + pad), min(h, y + sy + pad)
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
        ustate()["progress"] = int(progress[0] + (progress[1] - progress[0]) * (n + 1) / len(tiles))
    acc /= np.maximum(wsum, 1e-6)
    return acc

_max_session = None


def _max_x2(img, tile=320, pad=20, progress=(0, 100)):
    """Agrandissement ×2 « Qualité max » (Real-ESRGAN complet), par tuiles de taille paire."""
    global _max_session
    import numpy as np
    from PIL import Image
    if _max_session is None:
        _max_session = new_session(MODELS / "real_esrgan_x2.onnx")
    src = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    run = lambda part: _max_session.run(None, {"input": part.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
    out = _tiled(src, run, 2, tile, pad, progress, even=True)
    return Image.fromarray((out.clip(0, 1) * 255).round().astype(np.uint8))


SHARP_MODEL = MODELS / "nomos8k_sc_x4.onnx"   # netteté renforcée + qualité maximale (lourd, téléchargé)
SHARP_FAST_MODEL = __import__("pathlib").Path(__file__).resolve().parent / "models" / "sharp-x4.onnx"  # inclus
_sharp_session = _sharp_fast_session = None


def _sharp_x4(img, factor=2, heavy=False):
    """« Netteté renforcée » (façon Upscayl). Par défaut 4xLSDIRCompact (léger, ~20× plus rapide) ;
    heavy=True : 4xNomos8kSC, le plus fin, pour la qualité maximale."""
    global _sharp_session, _sharp_fast_session
    import numpy as np
    from PIL import Image
    if heavy:
        if _sharp_session is None:
            _sharp_session = new_session(SHARP_MODEL)
        sess, tile, pad = _sharp_session, 256, 12
    else:
        if _sharp_fast_session is None:
            _sharp_fast_session = new_session(SHARP_FAST_MODEL)
        sess, tile, pad = _sharp_fast_session, 512, 16
    w, h = img.size
    src = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    name = sess.get_inputs()[0].name
    ustate().update(busy=True, progress=0)
    try:
        run = lambda part: sess.run(None, {name: part.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
        out4 = _tiled(src, run, 4, tile, pad)
    finally:
        ustate()["busy"] = False
    res = Image.fromarray((out4.clip(0, 1) * 255).round().astype(np.uint8))
    if factor != 4:
        res = res.resize((w * factor, h * factor), Image.LANCZOS)
    # un peu d'agrandissement classique : grain réel, et adoucit les contours trop marqués du modèle léger
    return Image.blend(res, img.convert("RGB").resize(res.size, Image.LANCZOS), 0.12 if heavy else 0.22)


def upscale_image(img, factor=2, tile=640, pad=16, quality="fast"):
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
        ustate().update(busy=True, progress=0)
        try:
            res = _max_x2(img, progress=(0, 100 if factor == 2 else 50))
            if factor == 4:
                res = _max_x2(res, progress=(50, 100))
        finally:
            ustate()["busy"] = False
        # 25 % d'agrandissement classique : grain réel conservé
        return Image.blend(res, img.convert("RGB").resize(res.size, Image.LANCZOS), 0.25)
    if quality == "sharpmax" and pack_ready("sharp"):
        return _sharp_x4(img, factor, heavy=True)
    if quality in ("sharp", "sharpmax"):
        return _sharp_x4(img, factor)
    if _up_session is None:
        _up_session = new_session(UPSCALE_MODEL)
    src = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    ustate().update(busy=True, progress=0)
    try:
        run = lambda part: _up_session.run(None, {"input": part.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
        out4 = _tiled(src, run, 4, tile, pad)
        res = Image.fromarray((out4.clip(0, 1) * 255).round().astype(np.uint8))
        if factor != 4:  # ×4 puis réduction soignée : plus net qu'un ×2 direct
            res = res.resize((w * factor, h * factor), Image.LANCZOS)
        out = np.asarray(res)
    finally:
        ustate()["busy"] = False
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
    ustate().update(busy=True, progress=10)
    try:
        img, n = ai_face.restore(_decode(image_data_url, "RGB"), strength=float(strength), fidelity=1.0)
    finally:
        ustate().update(busy=False, progress=100)
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
            from . import gpu
            gpu.selftest(UPSCALE_MODEL)   # une fois après l'installation : carte graphique vraiment plus rapide ?
            if _up_session is None:
                _up_session = new_session(UPSCALE_MODEL)
            if _sharp_fast_session is None:
                globals()["_sharp_fast_session"] = new_session(SHARP_FAST_MODEL)
            if pack_ready("lama"):
                _get_session()
            if pack_ready("faces"):
                from . import ai_face
                ai_face._session(ai_face.DETECTOR[0])
                ai_face._session(ai_face.RESTORER[0])
                _download_optional("faces")   # visages rapides, pour ceux qui ont installé le paquet avant
                if ai_face._have(*ai_face.FAST_RESTORER):
                    ai_face._session(ai_face.FAST_RESTORER[0])
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()

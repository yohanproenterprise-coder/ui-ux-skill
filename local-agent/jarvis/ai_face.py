"""Restauration des visages : détection (YOLOface), alignement, restauration par IA, recollage invisible.

Priorité au naturel : le visage restauré est mélangé à l'original (intensité réglable), les contours
sont fondus progressivement et le grain de la photo est réinjecté pour éviter l'effet « lissé ».
"""

import os
import threading

import numpy as np

from .config import HOME

MODELS_DIR = HOME / "models"
BASE = "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/"
DETECTOR = ("yoloface_8n.onnx", 10_000_000)
RESTORER = ("codeformer.onnx", 300_000_000)
FAST_RESTORER = ("gpen_bfr_256.onnx", 70_000_000)   # 10× plus rapide, utilisé pour les visages petits et moyens
FAST_MAX = 180   # largeur de visage (px) jusqu'à laquelle le modèle rapide (256 px) suffit
# modèle de référence des 5 points du visage (yeux, nez, coins de la bouche) pour un visage 512×512
TEMPLATE = np.array([[0.37691676, 0.46864664], [0.62285697, 0.46912813], [0.50123859, 0.61331904],
                     [0.39308822, 0.72541100], [0.61150205, 0.72490465]], dtype=np.float32) * 512
_sessions, _lock = {}, threading.Lock()


def installed():
    return all((MODELS_DIR / n).exists() and (MODELS_DIR / n).stat().st_size > mn for n, mn in (DETECTOR, RESTORER))


def _have(n, mn):
    return (MODELS_DIR / n).exists() and (MODELS_DIR / n).stat().st_size > mn


def files_to_download(optional=True):
    return [(BASE + n, MODELS_DIR / n, mn) for n, mn in (DETECTOR, RESTORER) + ((FAST_RESTORER,) if optional else ())
            if not _have(n, mn)]


def _session(name):
    with _lock:
        if name not in _sessions:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            _sessions[name] = ort.InferenceSession(str(MODELS_DIR / name), sess_options=opts,
                                                   providers=["CPUExecutionProvider"])
        return _sessions[name]


def unload():
    with _lock:
        _sessions.clear()


# ------------------------------------------------------------------ détection --
def detect(rgb, min_score=0.5):
    """Renvoie [(score, boîte x0,y0,x1,y1, 5 points)] pour chaque visage."""
    from PIL import Image
    h, w = rgb.shape[:2]
    r = min(640 / w, 640 / h)
    small = np.asarray(Image.fromarray(rgb).resize((max(1, round(w * r)), max(1, round(h * r))), Image.BILINEAR))
    canvas = np.zeros((640, 640, 3), np.float32)
    canvas[:small.shape[0], :small.shape[1]] = small[:, :, ::-1]  # le modèle attend du BGR
    x = ((canvas - 127.5) / 128.0).transpose(2, 0, 1)[None]
    det = _session(DETECTOR[0]).run(None, {_session(DETECTOR[0]).get_inputs()[0].name: x})[0][0].T
    boxes, scores, kps = det[:, :4], det[:, 4], det[:, 5:]
    keep = scores > min_score
    boxes, scores, kps = boxes[keep], scores[keep], kps[keep]
    out = []
    order = np.argsort(-scores)
    taken = np.zeros(len(order), bool)
    for a, i in enumerate(order):  # suppression des doublons (NMS)
        if taken[a]:
            continue
        cx, cy, bw, bh = boxes[i]
        box = np.array([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2]) / r
        pts = kps[i].reshape(5, 3)[:, :2] / r
        out.append((float(scores[i]), box, pts))
        for b2 in range(a + 1, len(order)):
            j = order[b2]
            cx2, cy2, bw2, bh2 = boxes[j]
            ix = max(0, min(cx + bw / 2, cx2 + bw2 / 2) - max(cx - bw / 2, cx2 - bw2 / 2))
            iy = max(0, min(cy + bh / 2, cy2 + bh2 / 2) - max(cy - bh / 2, cy2 - bh2 / 2))
            if ix * iy / (bw * bh + bw2 * bh2 - ix * iy + 1e-6) > 0.4:
                taken[b2] = True
    return out


# ------------------------------------------------------------------ alignement --
def _similarity(src, dst):
    """Transformation (rotation + échelle + translation) qui envoie src sur dst (méthode d'Umeyama)."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    s, d = src - mu_s, dst - mu_d
    cov = d.T @ s / len(src)
    u, sig, vt = np.linalg.svd(cov)
    e = np.eye(2)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        e[1, 1] = -1
    rot = u @ e @ vt
    scale = (sig * np.diag(e)).sum() / (s ** 2).sum() * len(src)
    m = np.zeros((2, 3))
    m[:, :2] = scale * rot
    m[:, 2] = mu_d - scale * rot @ mu_s
    return m


def _warp(img, m, size):
    """Applique la transformation m (image source → image de sortie) avec Pillow."""
    from PIL import Image
    full = np.vstack([m, [0, 0, 1]])
    inv = np.linalg.inv(full)[:2].ravel()
    return img.transform(size, Image.AFFINE, tuple(inv), resample=Image.BICUBIC)


# ---------------------------------------------------------------- restauration --
def _restore_crop(crop, fidelity, model=RESTORER[0]):
    x = (np.asarray(crop, np.float32) / 255.0 - 0.5) / 0.5
    x = x.transpose(2, 0, 1)[None]
    sess = _session(model)
    feeds = {sess.get_inputs()[0].name: x}
    for inp in sess.get_inputs()[1:]:  # CodeFormer : poids de fidélité (1 = fidèle à l'original)
        feeds[inp.name] = np.array([fidelity], dtype=np.float64)
    y = sess.run(None, feeds)[0][0].transpose(1, 2, 0)
    return ((y.clip(-1, 1) + 1) / 2 * 255).round().astype(np.uint8)


def _mask(size=512):
    """Masque doux : plein au centre du visage, fondu progressif vers les bords."""
    from PIL import Image, ImageDraw, ImageFilter
    m = Image.new("L", (size, size), 0)
    pad = int(size * 0.1)
    ImageDraw.Draw(m).rounded_rectangle((pad, pad, size - pad, size - pad), radius=size // 5, fill=255)
    return m.filter(ImageFilter.GaussianBlur(size * 0.06))


MIN_FACE, MAX_FACE = 32, 380   # en pixels (largeur du visage détecté)


def restore(img, strength=0.7, fidelity=0.7, max_faces=8):
    """Restaure les visages d'une image PIL RGB. Renvoie (image, nombre de visages restaurés).
    Ignorés (gain de temps, ~4 s par visage) : les visages minuscules, où l'IA inventerait des traits, et les
    très grands, déjà plus détaillés que ce que l'IA produit (512 px)."""
    from PIL import Image, ImageFilter
    rgb = np.asarray(img.convert("RGB"))
    faces = [f for f in detect(rgb) if MIN_FACE <= f[1][2] - f[1][0] <= MAX_FACE]
    faces = sorted(faces, key=lambda f: -(f[1][2] - f[1][0]))[:max_faces]
    out = img.convert("RGB")
    fast_ok = _have(*FAST_RESTORER)
    masks = {}
    for _, box, pts in faces:
        # visage petit ou moyen : modèle rapide en 256 px (assez de détail) ; grand visage : CodeFormer en 512 px
        fast = fast_ok and (box[2] - box[0]) <= FAST_MAX
        size = 256 if fast else 512
        base_mask = masks.setdefault(size, _mask(size))
        m = _similarity(pts.astype(np.float64), TEMPLATE.astype(np.float64) * (size / 512))
        crop = _warp(out, m, (size, size))
        fixed = Image.fromarray(_restore_crop(crop, fidelity, FAST_RESTORER[0] if fast else RESTORER[0]))
        # grain naturel : on réinjecte la fine texture de la photo d'origine dans le visage restauré
        a = np.asarray(crop, np.float32)
        grain = a - np.asarray(crop.filter(ImageFilter.GaussianBlur(1.2)), np.float32)
        fixed = Image.fromarray((np.asarray(fixed, np.float32) + grain * 0.6).clip(0, 255).astype(np.uint8))
        back = np.linalg.inv(np.vstack([m, [0, 0, 1]]))[:2]
        # zone de la photo couverte par le visage restauré (on ne retravaille qu'elle)
        corners = np.array([[0, 0, 1], [size, 0, 1], [0, size, 1], [size, size, 1]], np.float64) @ back.T
        x0, y0 = np.floor(corners.min(0)).astype(int)
        x1, y1 = np.ceil(corners.max(0)).astype(int)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(out.width, x1), min(out.height, y1)
        if x1 - x0 < 2 or y1 - y0 < 2:
            continue
        shift = back.copy()
        shift[:, 2] -= [x0, y0]
        face_back = _warp(fixed, shift, (x1 - x0, y1 - y0))
        alpha = _warp(base_mask, shift, (x1 - x0, y1 - y0)).point(lambda v: int(v * strength))
        region = out.crop((x0, y0, x1, y1))
        out.paste(Image.composite(face_back, region, alpha), (x0, y0))
    return out, len(faces)

"""Mise en scène de produit : détourage par IA (BiRefNet, open source), décor généré (Flux via Pollinations,
open source) ou photo de l'utilisateur, puis incrustation dans le Studio (ombres, lumière, proportions).

Le produit n'est jamais redessiné par l'IA : ses pixels restent ceux de la photo d'origine, seul le fond change.
Seule la description du décor part sur internet, jamais la photo du produit.
"""

import base64
import io
import json
import re
import urllib.parse
import urllib.request

import numpy as np

from . import ai_inpaint

MODEL = ai_inpaint.MODELS / "birefnet-lite.onnx"
_session = None

COMMON = ", professional interior and product photography, photorealistic, high detail, no text, no people, no product"
SUFFIX = {  # la place laissée libre dépend de la façon dont le produit est installé
    "pose": ", empty surface in the foreground center with nothing on it" + COMMON,
    "suspendu": (", empty space in the upper center below the ceiling with no lamp and nothing hanging there, "
                 "no light fixture" + COMMON),
    "mural": ", plain empty wall area in the center with no lamp, no frame and no decoration on it" + COMMON,
}


# ------------------------------------------------------------------ détourage --
def _mask(img):
    """Masque du produit (0..1) à la taille de l'image, par BiRefNet (entrée 1024×1024)."""
    global _session
    from PIL import Image
    if _session is None:
        _session = ai_inpaint.new_session(MODEL)
    x = np.asarray(img.convert("RGB").resize((1024, 1024), Image.BILINEAR), np.float32)
    x = x / max(float(x.max()), 1e-6)
    x = ((x - (0.485, 0.456, 0.406)) / (0.229, 0.224, 0.225)).transpose(2, 0, 1)[None].astype(np.float32)
    y = _session.run(None, {_session.get_inputs()[0].name: x})[0][0, 0]
    y = 1 / (1 + np.exp(-y))
    y = (y - y.min()) / max(float(y.max() - y.min()), 1e-6)
    m = Image.fromarray((y * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR)
    return np.asarray(m, np.float32) / 255


def _keep_main(m):
    """Retire les petits morceaux isolés (reflets, bouts de décor) : ne garde que les parties importantes."""
    from PIL import Image
    h, w = m.shape
    k = 256 / max(h, w)
    sw, sh = max(1, int(w * k)), max(1, int(h * k))
    small = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((sw, sh), Image.BILINEAR)) > 127
    labels = np.zeros(small.shape, np.int32)
    sizes = [0]
    for y0 in range(sh):
        for x0 in range(sw):
            if small[y0, x0] and not labels[y0, x0]:
                n = len(sizes)
                stack, count = [(y0, x0)], 0
                labels[y0, x0] = n
                while stack:
                    y, x = stack.pop()
                    count += 1
                    for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= yy < sh and 0 <= xx < sw and small[yy, xx] and not labels[yy, xx]:
                            labels[yy, xx] = n
                            stack.append((yy, xx))
                sizes.append(count)
    if len(sizes) <= 2:
        return m
    biggest = max(sizes)
    drop = np.isin(labels, [i for i, s in enumerate(sizes) if i and s < biggest * .12])
    if not drop.any():
        return m
    # zone à effacer, agrandie à la taille réelle et un peu élargie pour emporter les bords
    big = Image.fromarray((drop * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    from PIL import ImageFilter
    big = np.asarray(big.filter(ImageFilter.MaxFilter(5)), np.float32) / 255
    return m * (1 - big)


def _box_blur(a, r):
    """Flou rapide (deux passes de moyenne glissante), sur un tableau HxW ou HxWxC."""
    for axis in (0, 1):
        for _ in range(2):
            pad = [(0, 0)] * a.ndim
            pad[axis] = (r + 1, r)
            c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
            hi = np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)
            a = (hi - lo) / (2 * r + 1)
    return a


def cutout(img):
    """Image PIL → produit détouré (RGBA, recadré au plus près). Les bords sont nettoyés de la couleur du fond."""
    from PIL import Image
    img = img.convert("RGB")
    m = _keep_main(_mask(img))
    a = np.clip((m - .06) / .88, 0, 1)
    rgb = np.asarray(img, np.float32)
    # couleur des bords : on reprend celle de l'intérieur du produit (sinon un liseré du fond reste visible)
    r = max(2, round(max(img.size) / 400))
    num = _box_blur(rgb * a[..., None], r)
    den = _box_blur(a, r)[..., None]
    fg = num / np.maximum(den, 1e-4)
    edge = ((a > .01) & (a < .97))[..., None]
    rgb = np.where(edge, fg, rgb)
    ys, xs = np.nonzero(a > .02)
    if not len(xs):
        raise RuntimeError("Aucun produit détecté sur cette photo.")
    x0, x1 = max(0, xs.min() - 2), min(img.width, xs.max() + 3)
    y0, y1 = max(0, ys.min() - 2), min(img.height, ys.max() + 3)
    out = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)[y0:y1, x0:x1]
    return Image.fromarray(out, "RGBA")


def cutout_data_url(data_url):
    if not ai_inpaint.pack_ready("cutout"):
        raise RuntimeError("L'IA de détourage n'est pas installée.")
    with ai_inpaint.user_priority():
        ai_inpaint.ustate().update(busy=True, progress=30, step="Détourage du produit…")
        try:
            res = cutout(ai_inpaint._decode(data_url, "RGB"))
        finally:
            ai_inpaint.ustate().update(busy=False, progress=100, step="")
    buf = io.BytesIO()
    res.save(buf, "PNG", compress_level=1)
    return {"image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
            "width": res.width, "height": res.height}


# --------------------------------------------------------------------- décor --
def background(prompt, width=1024, height=1024, seed=1, mount="pose"):
    """Génère un décor vide (sans le produit) à partir d'une description. Seul le texte part sur internet."""
    prompt = re.sub(r"\s+", " ", str(prompt or "")).strip()[:400]
    if not prompt:
        raise ValueError("Décris le décor souhaité, ou choisis une idée.")
    w = max(256, min(2048, int(width) // 16 * 16))
    h = max(256, min(2048, int(height) // 16 * 16))
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt + SUFFIX.get(mount, SUFFIX['pose']))}"
           f"?width={w}&height={h}&seed={int(seed)}&nologo=true&model=flux&enhance=false")
    req = urllib.request.Request(url, headers={"User-Agent": "Jarvis"})
    try:
        with urllib.request.urlopen(req, timeout=150) as r:
            data = r.read()
    except Exception as e:
        raise RuntimeError(f"le service de décors ne répond pas ({e}). Vérifie ta connexion, ou utilise ta propre "
                           "photo de décor.")
    kind = "png" if data[:4] == b"\x89PNG" else "jpeg" if data[:3] == b"\xff\xd8\xff" else \
        "webp" if data[8:12] == b"WEBP" else None
    if not kind:
        raise RuntimeError("le service de décors n'a pas renvoyé d'image. Réessaie dans un instant.")
    return {"image": f"data:image/{kind};base64," + base64.b64encode(data).decode()}


IDEAS_PROMPT = (
    "Tu es directeur artistique pour une boutique en ligne. Voici un produit détouré. Propose 4 décors réalistes "
    "et vendeurs, adaptés à ce produit (lieu, surface où le poser, lumière, ambiance), cohérents avec son usage et "
    "sa taille réelle. Si c'est un luminaire, tiens compte de son type (suspension, lampe à poser, lampadaire, "
    "applique) et propose des pièces où il est mis en valeur, plutôt en soirée. Réponds UNIQUEMENT avec du JSON : "
    "une liste de 4 objets {\"titre\": \"2 à 4 mots en français\", \"prompt\": \"description du décor VIDE "
    "(sans le produit), en anglais, 15 à 30 mots\", \"pose\": \"pose\" (posé sur une table ou au sol) ou "
    "\"suspendu\" (accroché au plafond) ou \"mural\" (fixé au mur)}.")


def ideas(brain, data_url):
    """Idées de décor adaptées au produit, proposées par l'IA de Jarvis qui regarde la photo."""
    from PIL import Image
    img = ai_inpaint._decode(data_url, "RGBA")
    img.thumbnail((512, 512))
    flat = Image.new("RGB", img.size, (255, 255, 255))
    flat.paste(img, mask=img.getchannel("A"))
    buf = io.BytesIO()
    flat.save(buf, "JPEG", quality=85)
    answer = brain.vision(IDEAS_PROMPT, {"mime": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()})
    m = re.search(r"\[.*\]", answer or "", re.S)
    try:
        items = json.loads(m.group(0)) if m else []
        out = [{"titre": str(i["titre"])[:40], "prompt": str(i["prompt"])[:300],
                "pose": i.get("pose") if i.get("pose") in SUFFIX else "pose"} for i in items
               if isinstance(i, dict) and i.get("titre") and i.get("prompt")][:6]
    except (ValueError, KeyError, TypeError):
        out = []
    if not out:
        raise RuntimeError("l'IA n'a pas pu proposer d'idées (" + (answer or "pas de réponse")[:150] + ")")
    return {"ideas": out}

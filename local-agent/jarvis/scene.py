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


def _labels(m):
    """Découpe le masque en morceaux séparés (sur une version réduite à 256 px) : (étiquettes, tailles, sw, sh)."""
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
    return labels, sizes


def _drop(m, labels, drop_ids):
    """Efface du masque (taille réelle) les morceaux indiqués."""
    from PIL import Image, ImageFilter
    h, w = m.shape
    drop = np.isin(labels, list(drop_ids))
    if not drop.any():
        return m
    # zone à effacer, agrandie à la taille réelle et un peu élargie pour emporter les bords
    big = Image.fromarray((drop * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    big = np.asarray(big.filter(ImageFilter.MaxFilter(5)), np.float32) / 255
    return m * (1 - big)


def _near(labels, keep, frac=.035):
    """Morceaux situés tout près des morceaux gardés (pieds fins, tiges, câbles coupés en pointillés par l'IA)."""
    from PIL import Image, ImageFilter
    zone = Image.fromarray((np.isin(labels, list(keep)) * 255).astype(np.uint8))
    for _ in range(max(1, round(max(labels.shape) * frac))):
        zone = zone.filter(ImageFilter.MaxFilter(3))
    return {int(i) for i in np.unique(labels[np.asarray(zone) > 0]) if i}


def _keep_main(m):
    """Retire les petits morceaux isolés (reflets, bouts de décor) : garde les parties importantes et tout ce
    qui les touche presque (les fines parties du produit)."""
    labels, sizes = _labels(m)
    if len(sizes) <= 2:
        return m
    biggest = max(sizes)
    keep = {i for i, s in enumerate(sizes) if i and s >= biggest * .12}
    keep |= _near(labels, keep)
    return _drop(m, labels, [i for i in range(1, len(sizes)) if i not in keep])


def _pick(m, box):
    """Ne garde que l'objet désigné par le cadre (coordonnées en pixels du masque) : les morceaux situés surtout
    dans le cadre. Les meubles, plantes ou décors qui ne font que l'effleurer sont retirés."""
    labels, sizes = _labels(m)
    if len(sizes) <= 1:
        return m
    h, w = m.shape
    sh, sw = labels.shape
    x0, y0, x1, y1 = box
    inside = np.zeros(labels.shape, bool)
    inside[max(0, int(y0 * sh / h)):max(1, int(np.ceil(y1 * sh / h))), max(0, int(x0 * sw / w)):max(1, int(np.ceil(x1 * sw / w)))] = True
    keep, best, best_in = set(), None, 0
    for i in range(1, len(sizes)):
        part = labels == i
        n_in = int((part & inside).sum())
        if n_in > best_in:
            best, best_in = i, n_in
        if n_in >= .5 * sizes[i]:
            keep.add(i)
    if not keep and best:
        keep.add(best)
    if not keep:
        return m
    biggest = max(sizes[i] for i in keep)
    keep = {i for i in keep if sizes[i] >= biggest * .15}   # feuilles, reflets, bouts de décor : retirés
    keep |= {i for i in _near(labels, keep, .02) if (labels == i)[inside].any()}   # fines parties du produit
    return _drop(m, labels, [i for i in range(1, len(sizes)) if i not in keep])


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


def _mask_hd(img):
    """Masque en deux passes quand le produit est petit dans la photo : l'IA le repère, puis analyse une zone
    carrée autour de lui (sans déformer l'image), avec bien plus de pixels pour les tiges, pieds et câbles."""
    m = _mask(img)
    W, H = img.size
    ys, xs = np.nonzero(m > .25)
    if not len(xs):
        return m
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    side = int(max(x1 - x0, y1 - y0) * 1.15) + 16
    if side * side > .45 * W * H or side >= min(W, H):
        return m                                    # le produit occupe déjà la photo : rien à gagner
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    X0 = min(max(0, cx - side // 2), W - side)
    Y0 = min(max(0, cy - side // 2), H - side)
    out = np.zeros_like(m)
    out[Y0:Y0 + side, X0:X0 + side] = _mask(img.crop((X0, Y0, X0 + side, Y0 + side)))
    return out


def cutout(img, box=None):
    """Image PIL → produit détouré (RGBA, recadré au plus près). Les bords sont nettoyés de la couleur du fond.
    box = (x0, y0, x1, y1) en fractions de l'image : le cadre tracé autour du produit. L'IA travaille alors sur
    cette zone (plus de détails) et ne garde que l'objet désigné, pas le décor autour."""
    from PIL import Image
    img = img.convert("RGB")
    ox = oy = 0
    if box:
        W, H = img.size
        x0, x1 = sorted(min(1., max(0., float(v))) for v in (box[0], box[2]))
        y0, y1 = sorted(min(1., max(0., float(v))) for v in (box[1], box[3]))
        mx, my = (x1 - x0) * .08, (y1 - y0) * .08            # petite marge : le produit peut dépasser du cadre
        X0, Y0 = max(0, int((x0 - mx) * W)), max(0, int((y0 - my) * H))
        X1, Y1 = min(W, int(np.ceil((x1 + mx) * W))), min(H, int(np.ceil((y1 + my) * H)))
        if X1 - X0 < 24 or Y1 - Y0 < 24:
            raise RuntimeError("Le cadre est trop petit : trace-le autour du produit entier.")
        img = img.crop((X0, Y0, X1, Y1))
        ox, oy = X0, Y0
        m = _pick(_mask_hd(img), (x0 * W - X0, y0 * H - Y0, x1 * W - X0, y1 * H - Y0))
    else:
        m = _keep_main(_mask_hd(img))
    _lb, _sz = _labels(m)
    parts = sum(1 for v in _sz[1:] if v >= .25 * max(_sz[1:] or [1]))   # objets séparés importants
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
    res = Image.fromarray(out, "RGBA")
    res.info["offset"] = (int(ox + x0), int(oy + y0))   # position dans la photo envoyée (pour la retouche)
    res.info["top_touch"] = y0 <= 2                       # le produit touche le haut de la zone analysée
    res.info["parts"] = parts
    return res


def cutout_data_url(data_url, box=None):
    if not ai_inpaint.pack_ready("cutout"):
        raise RuntimeError("L'IA de détourage n'est pas installée.")
    with ai_inpaint.user_priority():
        ai_inpaint.ustate().update(busy=True, progress=30, step="Détourage du produit…")
        try:
            res = cutout(ai_inpaint._decode(data_url, "RGB"), box)
        finally:
            ai_inpaint.ustate().update(busy=False, progress=100, step="")
    buf = io.BytesIO()
    res.save(buf, "PNG", compress_level=1)
    return {"image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
            "width": res.width, "height": res.height,
            "x": res.info.get("offset", (0, 0))[0], "y": res.info.get("offset", (0, 0))[1]}


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


# ------------------------------------------------------------------------------------------- fond studio --
STUDIO_COLORS = {"blanc": "#ffffff", "gris": "#eeeeec", "beige": "#f1ebe2", "noir": "#161616"}


class StudioAmbiguous(RuntimeError):
    """Plusieurs objets séparés sur la photo : impossible de savoir lequel est le produit sans le montrer."""


def studio(img, color="#ffffff", margin=.08, shadow=.6, box=None, strict=False):
    """Photo « packshot » : le produit est détouré et posé sur un fond studio uni, centré avec des marges
    régulières (les mêmes sur toutes les photos d'une collection), avec une ombre douce au sol.
    Le produit n'est jamais redessiné. Un luminaire suspendu (câble qui part du haut de la photo) reste accroché
    en haut, sans ombre au sol. La photo garde sa taille et son format."""
    from PIL import Image, ImageDraw, ImageFilter
    img = img.convert("RGB")
    W, H = img.size
    color = STUDIO_COLORS.get(color, color)
    rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    cut = cutout(img, box)
    if strict and not box and cut.info.get("parts", 1) > 1:
        raise StudioAmbiguous("plusieurs objets sur la photo : fond studio à faire dans le Studio en montrant le produit (🎯)")
    ox, oy = cut.info.get("offset", (0, 0))
    # suspension : le produit part du haut (câble, tige) avec une partie fine en haut et large en dessous
    al = np.asarray(cut.split()[3]) > 80
    widths = al.sum(axis=1)
    top = widths[:max(2, len(widths) // 8)]
    hanging = bool(cut.info.get("top_touch")) and widths.max() > 0 and top.mean() < widths.max() * .3
    # taille : le produit remplit la zone utile, sans être agrandi plus de 1,6× (resterait flou)
    room_w, room_h = W * (1 - 2 * margin), H * (1 - 2 * margin) * (1 if hanging else .94)
    k = min(room_w / cut.width, room_h / cut.height, 1.6)
    cw, ch = max(1, round(cut.width * k)), max(1, round(cut.height * k))
    prod = cut.resize((cw, ch), Image.LANCZOS)
    x = (W - cw) // 2
    if hanging:
        y = max(0, int(H * (1 - margin * 1.6)) - ch)       # le luminaire dans le haut-milieu, câble jusqu'au plafond
        if y > 0:   # on prolonge le câble jusqu'en haut de la photo
            strip = prod.crop((0, 0, cw, max(1, ch // 60))).resize((cw, y), Image.NEAREST)
            prod_full = Image.new("RGBA", (cw, ch + y), (0, 0, 0, 0))
            prod_full.paste(strip, (0, 0)); prod_full.paste(prod, (0, y))
            prod, ch, y = prod_full, ch + y, 0
    else:
        y = int(H * margin + (room_h - ch) / 2 + (H * (1 - 2 * margin) - room_h) * .2)
    # fond : uni ; pour les teintes autres que le blanc pur, une très légère lumière au centre (rendu « studio »)
    bg = Image.new("RGB", (W, H), rgb)
    if rgb != (255, 255, 255):
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W * .7)) ** 2 + ((yy - H * .45) / (H * .8)) ** 2)
        light = (np.clip(1 - r, 0, 1) ** 1.5 * (14 if sum(rgb) > 200 else 22))[..., None]
        bg = Image.fromarray(np.clip(np.asarray(bg, np.float32) + light, 0, 255).astype(np.uint8))
    canvas = bg.convert("RGBA")
    if shadow > 0 and not hanging:
        a = prod.split()[3]
        # ombre de contact (sous la base) + ombre portée douce
        ys, xs = np.nonzero(np.asarray(a)[-max(3, ch // 12):] > 60)
        sh = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(sh)
        if len(xs):
            bx0, bx1 = x + xs.min(), x + xs.max()
            d.ellipse((bx0 - cw * .04, y + ch - ch * .025, bx1 + cw * .04, y + ch + ch * .035), fill=int(150 * shadow))
        sh = sh.filter(ImageFilter.GaussianBlur(max(3, ch * .02)))
        drop = Image.new("L", (W, H), 0)
        drop.paste(a.point(lambda v: v * .35 * shadow), (x, y + int(ch * .015)))
        drop = drop.filter(ImageFilter.GaussianBlur(max(4, ch * .035)))
        both = Image.fromarray(np.maximum(np.asarray(sh), np.asarray(drop)))
        tone = tuple(int(c * .55) for c in rgb)
        canvas = Image.composite(Image.new("RGBA", (W, H), tone + (255,)), canvas, both)
    canvas.alpha_composite(prod, (x, y))
    return canvas.convert("RGB")


def studio_data_url(data_url, color="#ffffff", box=None):
    if not ai_inpaint.pack_ready("cutout"):
        raise RuntimeError("L'IA de détourage n'est pas installée (onglet Mise en scène).")
    with ai_inpaint.user_priority():
        ai_inpaint.ustate().update(busy=True, progress=40, step="Fond studio…")
        try:
            res = studio(ai_inpaint._decode(data_url, "RGB"), color, box=box)
        finally:
            ai_inpaint.ustate().update(busy=False, progress=100, step="")
    buf = io.BytesIO()
    res.save(buf, "PNG", compress_level=1)
    return {"image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}

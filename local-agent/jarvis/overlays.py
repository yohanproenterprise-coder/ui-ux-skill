"""Repère ce qui a été AJOUTÉ sur une photo produit et ne fait pas partie du produit : textes, prix, filigranes,
logos, pastilles, icônes et formes colorées. Le résultat est un masque que la gomme magique efface ensuite.

- Textes : détecteur PaddleOCR PP-OCRv3 (Apache 2.0, 2,4 Mo, livré avec Jarvis), toutes langues et écritures.
- Formes et logos : parties « saillantes » séparées du produit et de couleur unie (IA de détourage, si installée).
- Le produit lui-même est protégé : son logo ou son texte imprimé n'est jamais effacé.
"""

import base64
import io
from pathlib import Path

import numpy as np

from . import ai_inpaint

TEXT_MODEL = Path(__file__).resolve().parent / "models" / "text-det.onnx"
_text = None


def _text_map(img):
    """Probabilité « texte » (0..1) pour chaque pixel, à la taille de l'image."""
    global _text
    from PIL import Image
    if _text is None:
        _text = ai_inpaint.new_session(TEXT_MODEL)
    w, h = img.size
    # petites photos (fournisseurs) agrandies pour que les petits textes soient vus ; les autres jusqu'à 1280 px
    k = 1280 / max(w, h) if max(w, h) < 700 else min(1., 1280 / max(w, h))
    tw, th = max(32, round(w * k / 32) * 32), max(32, round(h * k / 32) * 32)
    x = np.asarray(img.convert("RGB").resize((tw, th), Image.BICUBIC), np.float32) / 255
    x = ((x - (.485, .456, .406)) / (.229, .224, .225)).transpose(2, 0, 1)[None].astype(np.float32)
    prob = _text.run(None, {_text.get_inputs()[0].name: x})[0][0, 0]
    m = Image.fromarray((np.clip(prob, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(m, np.float32) / 255


def _grow(mask, frac):
    """Élargit un masque binaire (calcul sur une version réduite, rapide même sur une grande photo)."""
    from PIL import Image, ImageFilter
    h, w = mask.shape
    k = min(1., 900 / max(w, h))
    small = Image.fromarray((mask * 255).astype(np.uint8)).resize((max(1, int(w * k)), max(1, int(h * k))), Image.BILINEAR)
    for _ in range(max(1, round(max(small.size) * frac))):
        small = small.filter(ImageFilter.MaxFilter(3))
    return np.asarray(small.resize((w, h), Image.BILINEAR)) > 40


def _runs(on, min_len, gap=3):
    """Pour chaque ligne d'un tableau booléen, marque les segments continus (trous ≤ gap) d'au moins min_len pixels."""
    out = np.zeros_like(on)
    for y in np.nonzero(on.sum(axis=1) >= min_len * .7)[0]:
        xs = np.nonzero(on[y])[0]
        start = prev = xs[0]
        for x in list(xs[1:]) + [None]:
            if x is not None and x - prev <= gap + 1:
                prev = x
                continue
            if prev - start + 1 >= min_len:
                out[y, start:prev + 1] = True
            if x is not None:
                start = prev = x
    return out


def _lines(img):
    """Traits fins, droits, horizontaux ou verticaux (lignes de cote, flèches, soulignements) : contraste net des deux
    côtés du trait, sur au moins 6 % de la largeur de la photo."""
    from PIL import Image
    w, h = img.size
    k = min(1., 1000 / max(w, h))
    g = np.asarray(img.convert("L").resize((max(8, int(w * k)), max(8, int(h * k))), Image.BILINEAR), np.float32)
    H, W = g.shape
    res = np.zeros((H, W), bool)
    for t in (1, 2, 3):                               # épaisseur du trait
        up, down = np.roll(g, t + 1, 0), np.roll(g, -(t + 1), 0)
        hor = (np.abs(g - up) > 35) & (np.abs(g - down) > 35) & (np.sign(g - up) == np.sign(g - down))
        hor[:t + 1], hor[-t - 1:] = False, False
        res |= _runs(hor, int(W * .06))
        left, right = np.roll(g, t + 1, 1), np.roll(g, -(t + 1), 1)
        ver = (np.abs(g - left) > 35) & (np.abs(g - right) > 35) & (np.sign(g - left) == np.sign(g - right))
        ver[:, :t + 1], ver[:, -t - 1:] = False, False
        res |= _runs(ver.T, int(H * .06)).T
    return np.asarray(Image.fromarray(res.astype(np.uint8) * 255).resize((w, h), Image.NEAREST)) > 0


def _dilate(mask, r):
    """Dilatation carrée de rayon r (pixels), rapide : décalages successifs par puissances de deux."""
    out = mask.copy()
    for axis in (0, 1):
        done, step = 0, 1
        while done < r:
            s = min(step, r - done)
            shifted = out.copy()
            if axis == 0:
                shifted[s:] |= out[:-s]; shifted[:-s] |= out[s:]
            else:
                shifted[:, s:] |= out[:, :-s]; shifted[:, :-s] |= out[:, s:]
            out = shifted
            done += s
            step *= 2
    return out


def _unclip(text):
    """Le détecteur (DBNet) ne renvoie que le cœur des lettres, rétréci. Comme PaddleOCR, on rend à chaque mot sa
    vraie taille, proportionnellement à son épaisseur (≈ 0,8 × hauteur du cœur), plus une marge pour les contours
    adoucis et les ombres portées."""
    from PIL import Image
    from . import scene
    if not text.any():
        return text
    h, w = text.shape
    labels, sizes = scene._labels(text.astype(np.float32))
    sh, sw = labels.shape
    out = np.zeros_like(text)
    for i in range(1, len(sizes)):
        ys, xs = np.nonzero(labels == i)
        X0, Y0 = int(xs.min() * w / sw), int(ys.min() * h / sh)
        X1, Y1 = min(w, int(np.ceil((xs.max() + 1) * w / sw))), min(h, int(np.ceil((ys.max() + 1) * h / sh)))
        blob = text[Y0:Y1, X0:X1]
        if not blob.any():
            continue
        thick = blob.sum() / max(1, max(blob.shape))        # épaisseur moyenne du cœur
        r = int(thick * .85 + 4 + max(w, h) * .003)
        x0, y0, x1, y1 = max(0, X0 - r), max(0, Y0 - r), min(w, X1 + r), min(h, Y1 + r)
        out[y0:y1, x0:x1] |= _dilate(text[y0:y1, x0:x1], r)
    return out


def _badges(img, words, product):
    """Un texte posé sur une étiquette ou une pastille de couleur unie (prix, « promo »…) : l'étiquette entière est
    ajoutée à la zone à effacer. On part de la couleur juste autour du mot et on suit la zone de cette couleur ; si
    elle reste fermée (elle ne s'étend pas à tout le fond), c'est une étiquette."""
    from PIL import Image
    from . import scene
    out = np.zeros_like(words)
    if not words.any():
        return out
    h, w = words.shape
    arr = np.asarray(img.convert("RGB"), np.float32)
    labels, sizes = scene._labels(words.astype(np.float32))
    sh, sw = labels.shape
    for i in range(1, len(sizes)):
        ys, xs = np.nonzero(labels == i)
        x0, y0 = int(xs.min() * w / sw), int(ys.min() * h / sh)
        x1, y1 = min(w, int(np.ceil((xs.max() + 1) * w / sw))), min(h, int(np.ceil((ys.max() + 1) * h / sh)))
        bw, bh = x1 - x0, y1 - y0
        X0, Y0, X1, Y1 = max(0, x0 - bw), max(0, y0 - bh * 2), min(w, x1 + bw), min(h, y1 + bh * 2)
        win, wd = arr[Y0:Y1, X0:X1], words[Y0:Y1, X0:X1]
        ring = _dilate(wd, max(3, bh // 6)) & ~wd
        if ring.sum() < 20 or product[Y0:Y1, X0:X1][ring].mean() > .3:
            continue
        ref = np.median(win[ring], axis=0)
        same = (np.abs(win - ref).max(axis=2) < 30) & ~product[Y0:Y1, X0:X1]
        # zone de cette couleur reliée au pourtour du mot (croissance limitée à la fenêtre)
        reg = ring & same
        for _ in range(max(win.shape)):
            nxt = _dilate(reg, 1) & (same | wd)
            if nxt.sum() == reg.sum():
                break
            reg = nxt
        border = np.concatenate([reg[0], reg[-1], reg[:, 0], reg[:, -1]])
        if border.mean() > .04 or reg.sum() < ring.sum():   # s'étend jusqu'au bord de la fenêtre : c'est le fond
            continue
        ry, rx = np.nonzero(reg | wd)
        box = np.zeros_like(wd)
        box[ry.min():ry.max() + 1, rx.min():rx.max() + 1] = True
        # l'étiquette : sa zone colorée, les lettres et ce qu'elles enferment (rectangle englobant si forme pleine)
        fill = reg | wd | (box & _dilate(reg, 2))
        # marge généreuse : le bord d'une étiquette est adouci (anticrénelage, compression), il laisserait un contour
        out[Y0:Y1, X0:X1] |= _dilate(fill, max(4, int(.1 * min(np.ptp(ry) + 1, np.ptp(rx) + 1))))
    return out


def _confident(prob):
    """Zones de texte (seuil 0,3 comme PaddleOCR), mais on ne garde que celles où le détecteur est vraiment sûr
    de lui quelque part (vrai mot : cœur très net). Feuilles, cordons, motifs : écartés."""
    from . import scene
    text = prob > .3
    if not text.any():
        return text
    labels, sizes = scene._labels(text.astype(np.float32))
    sh, sw = labels.shape
    h, w = text.shape
    keep = np.zeros((sh, sw), bool)
    from PIL import Image
    small_p = np.asarray(Image.fromarray((prob * 255).astype(np.uint8)).resize((sw, sh), Image.BILINEAR), np.float32) / 255
    for i in range(1, len(sizes)):
        part = labels == i
        vals = np.sort(small_p[part])[::-1]
        q = vals[:max(1, len(vals) // 4)].mean()           # le quart le plus net de la zone
        # vrai mot : cœur très net, ou zone assez grande et nette ; minuscules taches incertaines écartées
        if (q >= .95 and sizes[i] >= 4) or (q > .8 and sizes[i] >= 25):
            keep |= part
    big = np.asarray(Image.fromarray(keep.astype(np.uint8) * 255).resize((w, h), Image.NEAREST)) > 0
    return text & big


def detect(img):
    """Image PIL → (masque booléen des éléments ajoutés, nombre de textes, nombre de formes)."""
    from PIL import Image
    from . import scene
    img = img.convert("RGB")
    w, h = img.size
    text = _confident(_text_map(img))
    product = np.zeros((h, w), bool)
    shapes = np.zeros((h, w), bool)
    n_shapes = 0
    if ai_inpaint.pack_ready("cutout"):
        m = scene._mask(img)
        labels, sizes = scene._labels(m)
        if len(sizes) > 1:
            sh, sw = labels.shape
            small_rgb = np.asarray(img.resize((sw, sh), Image.BILINEAR), np.float32)
            small_text = np.asarray(Image.fromarray(text.astype(np.uint8) * 255).resize((sw, sh))) > 0
            flat, texty = {}, {}
            for i in range(1, len(sizes)):
                part = labels == i
                px = small_rgb[part]
                # pastille, logo, icône : une couleur domine nettement (même avec des lettres dessus)
                uni = (np.abs(px - np.median(px, axis=0)).max(axis=1) < 22).mean()
                ys_, xs_ = np.nonzero(part)
                solid = sizes[i] / max(1, (np.ptp(ys_) + 1) * (np.ptp(xs_) + 1))
                touches_text = (_dilate(part, 2) & small_text).any()
                # forme ajoutée : aplat qui porte un texte (pastille, étiquette), ou aplat franc, net et compact
                # (une feuille, un bout de tissu ou de bois n'en est pas : couleur moins uniforme, forme découpée)
                flat[i] = (uni > .6 and touches_text) or (uni > .85 and solid > .6 and sizes[i] > 30)
                texty[i] = (part & small_text).sum() > .3 * sizes[i]         # lettre ou bloc de texte
            # protégés : tous les objets à vraie texture (le produit, les meubles…). Une pastille unie ou un texte
            # ajouté n'en fait pas partie.
            main = {i for i in range(1, len(sizes)) if not flat[i] and not texty[i]}
            if main:
                product = part_full(np.isin(labels, list(main)), w, h) & (m > .5)
            for i in range(1, len(sizes)):
                if i in main or sizes[i] < 4:
                    continue
                if flat[i] or texty[i]:
                    shapes |= part_full(labels == i, w, h) & (m > .3)
                    n_shapes += 0 if texty[i] else 1
    text = _overlay_text(text, product)    # texte imprimé sur le produit : gardé ; texte ajouté qui le chevauche : effacé
    # textes : on compte les blocs séparés
    tl, ts = scene._labels(text.astype(np.float32))
    n_text = len(ts) - 1
    # lignes de cote : seulement près d'un texte ajouté (« 25 cm »…), jamais sur le produit
    lines = np.zeros((h, w), bool)
    if text.any():
        lines = _lines(img) & _grow(text, .06) & ~product
    words = _unclip(text)
    words |= _badges(img, words, product)       # étiquette prix, pastille : le fond coloré du texte part avec lui
    erase = words | _grow(shapes, .005) | _grow(lines, .009)   # marge : contours adoucis, pointes de flèche, ombres
    erase &= ~(product & ~words)                               # jamais sur le produit (sauf texte qui le chevauche)
    if lines.any():
        n_shapes += len(scene._labels(lines.astype(np.float32))[1]) - 1
    return erase, n_text, n_shapes


def _overlay_text(text, product):
    """Sépare le texte imprimé SUR le produit (gardé) du texte ajouté par-dessus la photo (effacé), même quand ce
    dernier chevauche le produit : on regarde ce qui entoure chaque mot. Un mot entièrement entouré de produit est
    imprimé dessus ; un mot dont le pourtour déborde sur le fond a été ajouté, et il est effacé en entier."""
    from PIL import Image
    from . import scene
    if not text.any() or not product.any():
        return text
    h, w = text.shape
    k = min(1., 700 / max(w, h))
    sw, sh = max(8, int(w * k)), max(8, int(h * k))
    small = lambda m: np.asarray(Image.fromarray(m.astype(np.uint8) * 255).resize((sw, sh), Image.BILINEAR)) > 100
    t, prod = small(text), small(product)
    words = _grow(t, .012)                                   # les lettres d'un même mot ou d'une même ligne ensemble
    ring = _grow(words, .012) & ~words
    labels, sizes = scene._labels(words.astype(np.float32))
    lab = np.asarray(Image.fromarray(labels.astype(np.int32).astype(np.uint16)).resize((sw, sh), Image.NEAREST)).astype(np.int32) \
        if labels.shape != (sh, sw) else labels
    keep_printed = np.zeros((sh, sw), bool)
    for i in range(1, len(sizes)):
        blob = lab == i
        rb = _grow(blob, .012) & ring
        if rb.sum() < 8:
            continue
        on_ring = (prod & rb).sum() / max(1, rb.sum())
        on_word = (prod & blob).sum() / max(1, blob.sum())
        # imprimé (ou simple matière du produit) : pourtour entièrement sur le produit, ou mot surtout posé dessus.
        # Texte ajouté : la plus grande partie déborde sur le fond, il est alors effacé en entier.
        if on_ring > .9 or on_word >= .5:
            keep_printed |= blob
    if not keep_printed.any():
        return text
    return text & ~(np.asarray(Image.fromarray(keep_printed.astype(np.uint8) * 255).resize((w, h), Image.NEAREST)) > 0)


def part_full(small_mask, w, h):
    from PIL import Image
    return np.asarray(Image.fromarray(small_mask.astype(np.uint8) * 255).resize((w, h), Image.NEAREST)) > 0


def detect_data_url(data_url):
    """Renvoie le masque sous forme d'image (rose semi-opaque, comme le pinceau de la gomme) et le décompte."""
    from PIL import Image
    with ai_inpaint.user_priority():
        ai_inpaint.ustate().update(busy=True, progress=40, step="Recherche des textes et logos ajoutés…")
        try:
            erase, n_text, n_shapes = detect(ai_inpaint._decode(data_url, "RGB"))
        finally:
            ai_inpaint.ustate().update(busy=False, progress=100, step="")
    h, w = erase.shape
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[erase] = (255, 61, 110, 255)
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", compress_level=1)
    return {"mask": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
            "texts": int(n_text), "shapes": int(n_shapes), "found": bool(erase.any()),
            "protected": ai_inpaint.pack_ready("cutout")}


# ------------------------------------------------------------------ effacement automatique, bords du produit nets --
def _b64(img, fmt="PNG"):
    buf = io.BytesIO()
    img.save(buf, fmt, compress_level=1) if fmt == "PNG" else img.save(buf, fmt, quality=95)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def _zones(hole):
    """Zones séparées du masque (un mot, un logo…) : rectangles en pixels de l'image."""
    from . import scene
    h, w = hole.shape
    labels, sizes = scene._labels(_grow(hole, .015).astype(np.float32))
    sh, sw = labels.shape
    out = []
    for i in range(1, len(sizes)):
        ys, xs = np.nonzero(labels == i)
        out.append((int(xs.min() * w / sw), int(ys.min() * h / sh), int(np.ceil((xs.max() + 1) * w / sw)), int(np.ceil((ys.max() + 1) * h / sh))))
    return out


def _lama(img, hole):
    """Reconstruit les pixels de `hole` avec l'IA LaMa, zone par zone (chaque zone avec son contexte proche, en
    pleine définition), et ne change rien en dehors du masque."""
    from PIL import Image, ImageFilter
    out = img.copy()
    w, h = img.size
    for x0, y0, x1, y1 in _zones(hole):
        m = int(max(x1 - x0, y1 - y0) * .6) + 40
        X0, Y0, X1, Y1 = max(0, x0 - m), max(0, y0 - m), min(w, x1 + m), min(h, y1 + m)
        crop = out.crop((X0, Y0, X1, Y1))
        mk = Image.fromarray((hole[Y0:Y1, X0:X1] * 255).astype(np.uint8))
        if not np.asarray(mk).any():
            continue
        res = ai_inpaint._decode(ai_inpaint.inpaint(_b64(crop), _b64(mk)), "RGB")
        alpha = mk.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
        out.paste(Image.composite(res, crop, alpha), (X0, Y0))
    return out


def clean(img):
    """Efface tout seul textes, logos et lignes ajoutés. Quand un texte chevauche le produit :
    1) un premier effacement retire le texte ; 2) le produit est détouré à nouveau sur cette image propre, ce qui
    donne sa vraie silhouette sous le texte ; 3) le produit est reconstruit à partir de sa propre matière, le fond à
    partir du fond, puis les deux sont réunis le long de la silhouette : bord du produit net, sans bavure."""
    from PIL import Image, ImageFilter
    from . import scene
    img = img.convert("RGB")
    erase, n_text, n_shapes = detect(img)
    if not erase.any():
        return img, 0, 0
    ai_inpaint.ustate().update(busy=True, progress=35, step="Effacement des textes et logos…")
    rough = _lama(img, erase)
    if not ai_inpaint.pack_ready("cutout"):
        return rough, n_text, n_shapes
    ai_inpaint.ustate().update(busy=True, progress=60, step="Silhouette du produit sous le texte…")
    alpha = scene._mask(rough)                               # silhouette sur l'image sans texte (0..1)
    fg = alpha > .5
    near = _grow(erase, .02)
    crossing = erase & _grow(fg, .004) & _grow(~fg, .004)     # zones effacées qui touchent le bord d'un objet
    if not crossing.any():
        return rough, n_text, n_shapes
    ai_inpaint.ustate().update(busy=True, progress=75, step="Reconstruction du produit et du fond…")
    # objet : reconstruit à partir de lui-même (le fond voisin est masqué) ; fond : à partir du fond seul
    obj = _lama(img, erase | (near & ~fg))
    bg = _lama(img, erase | (near & fg))
    a = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.6)), np.float32)[..., None] / 255
    merged = (np.asarray(obj, np.float32) * a + np.asarray(bg, np.float32) * (1 - a))
    zone = np.asarray(Image.fromarray(_grow(erase, .004).astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255
    out = merged * zone + np.asarray(rough, np.float32) * (1 - zone)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), n_text, n_shapes


def clean_data_url(data_url):
    from PIL import Image
    if not ai_inpaint.pack_ready("lama"):
        raise RuntimeError("L'IA de retouche (LaMa) n'est pas installée : active le moteur « ✦ IA » de la gomme magique.")
    with ai_inpaint.user_priority():
        ai_inpaint.ustate().update(busy=True, progress=10, step="Recherche des textes et logos ajoutés…")
        try:
            out, n_text, n_shapes = clean(ai_inpaint._decode(data_url, "RGB"))
        finally:
            ai_inpaint.ustate().update(busy=False, progress=100, step="")
    return {"image": _b64(out), "texts": int(n_text), "shapes": int(n_shapes), "found": bool(n_text or n_shapes)}

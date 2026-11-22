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
    k = min(1., 1280 / max(w, h))
    tw, th = max(32, round(w * k / 32) * 32), max(32, round(h * k / 32) * 32)
    x = np.asarray(img.convert("RGB").resize((tw, th), Image.BILINEAR), np.float32) / 255
    x = ((x - (.485, .456, .406)) / (.229, .224, .225)).transpose(2, 0, 1)[None].astype(np.float32)
    p = _text.run(None, {_text.get_inputs()[0].name: x})[0][0, 0]
    m = Image.fromarray((np.clip(p, 0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
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


def detect(img):
    """Image PIL → (masque booléen des éléments ajoutés, nombre de textes, nombre de formes)."""
    from PIL import Image
    from . import scene
    img = img.convert("RGB")
    w, h = img.size
    text = _text_map(img) > .3
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
                flat[i] = (np.abs(px - np.median(px, axis=0)).max(axis=1) < 22).mean() > .6
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
    text &= ~product                                          # le texte imprimé sur le produit reste
    # textes : on compte les blocs séparés
    tl, ts = scene._labels(text.astype(np.float32))
    n_text = len(ts) - 1
    # lignes de cote : seulement près d'un texte ajouté (« 25 cm »…), jamais sur le produit
    lines = np.zeros((h, w), bool)
    if text.any():
        lines = _lines(img) & _grow(text, .06) & ~product
    erase = _grow(text, .011) | _grow(shapes, .005) | _grow(lines, .004)   # marge : contours adoucis, ombres, halos
    erase &= ~(product & ~_grow(text, .011))                  # jamais sur le produit (sauf texte qui le chevauche)
    if lines.any():
        n_shapes += len(scene._labels(lines.astype(np.float32))[1]) - 1
    return erase, n_text, n_shapes


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

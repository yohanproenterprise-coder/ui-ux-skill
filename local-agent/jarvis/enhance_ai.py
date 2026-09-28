"""Amélioration en un clic, inspirée de Claid.ai « Enhance » : aucun réglage, tout est décidé selon la photo.

Étapes : 1) nettoyage par IA (compression JPEG, bruit, netteté) avec Real-ESRGAN, à taille égale ou ×2
pour les petites photos ; 2) visages restaurés fidèlement (CodeFormer) ; 3) lumière et couleurs
équilibrées façon « HDR léger ». Priorité absolue : un rendu naturel.
"""

import numpy as np

from . import ai_inpaint

SMALL = 1200   # en dessous (plus grand côté), la photo est agrandie ×2 comme sur Claid
LARGE = 2600   # au-dessus, le nettoyage par IA serait trop long sur un PC sans carte graphique


def _progress(p, step):
    ai_inpaint.upscale_state.update(busy=True, progress=int(p), step=step)


def _blur(a, r):
    from PIL import Image, ImageFilter
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def light_and_color(img):
    """Lumière et couleurs naturelles : niveaux prudents, ombres débouchées localement, vibrance douce."""
    from PIL import Image
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    small = np.asarray(img.convert("RGB").resize((max(1, img.width // 4), max(1, img.height // 4))), np.float32) / 255.0
    lum_s = small @ np.array([.299, .587, .114], np.float32)
    lo, hi, mid = np.percentile(lum_s, [0.4, 99.6, 50])
    lo = min(lo, 0.16) * 0.6                     # on ne noircit jamais franchement
    hi = 1 - (1 - max(hi, 0.75)) * 0.6
    # balance des blancs très légère sur les tons neutres (l'ambiance chaude ou froide reste)
    sat_s = small.max(2) - small.min(2)
    neutral = (sat_s < .18) & (lum_s > .15) & (lum_s < .9)
    gains = np.ones(3, np.float32)
    if neutral.mean() > .03:
        m = small[neutral].mean(0)
        gains = np.clip(m.mean() / m, .97, 1.03)
    a = a * gains
    # niveaux + tons moyens (même courbe sur les 3 couches)
    a = np.clip((a - lo) / max(1e-3, hi - lo), 0, 1)
    mid_n = np.clip((mid - lo) / max(1e-3, hi - lo), .05, .95)
    gamma = 1 + (np.clip(np.log(.46) / np.log(mid_n), .82, 1.18) - 1) * .5
    a = a ** gamma
    # HDR léger : ombres débouchées et hautes lumières retenues, selon la luminosité locale
    lum = a @ np.array([.299, .587, .114], np.float32)
    local = _blur(lum, max(3, min(img.size) * .03))
    gain = 1 + .22 * np.clip(.42 - local, 0, .42) / .42 - .08 * np.clip(local - .78, 0, .22) / .22
    a = a * gain[..., None]
    # contraste doux (courbe en S très légère) et vibrance modérée, peau protégée
    a = np.clip(a, 0, 1)
    a = a + (a * a * (3 - 2 * a) - a) * .12
    lum = a @ np.array([.299, .587, .114], np.float32)
    sat = a.max(2) - a.min(2)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    skin = (r > g) & (g > b) & (r - b > .06) & (r - b < .5)
    k = 1 + .10 * (1 - sat) ** 2 * np.where(skin, .25, 1)
    a = lum[..., None] + (a - lum[..., None]) * k[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))


def enhance(img):
    """Renvoie (image améliorée, liste des étapes réalisées)."""
    from PIL import Image
    from . import ai_face
    img = img.convert("RGB")
    w, h = img.size
    done = []
    quality = "max" if ai_inpaint.pack_ready("upmax") else "fast"
    try:
        # 1. nettoyage et netteté par IA
        if max(w, h) <= LARGE:
            _progress(2, "Nettoyage de la photo par l'IA…")
            sr = ai_inpaint.upscale_image(img, 2, quality=quality)
            if max(w, h) < SMALL:
                out = sr
                done.append(f"agrandie ×2 ({sr.width}×{sr.height})")
            else:
                out = sr.resize((w, h), Image.LANCZOS)  # super-échantillonnage : plus propre à taille égale
            done.append("compression et bruit nettoyés, netteté restaurée")
        else:
            out = img
            done.append("photo déjà en haute résolution : nettoyage IA non nécessaire")
        # 2. visages
        if ai_inpaint.pack_ready("faces"):
            _progress(75, "Restauration des visages…")
            out, n = ai_face.restore(out, strength=.6, fidelity=1.0)
            if n:
                done.append(f"{n} visage{'s' if n > 1 else ''} restauré{'s' if n > 1 else ''}")
        # 3. lumière et couleurs
        _progress(90, "Lumière et couleurs…")
        out = light_and_color(out)
        done.append("lumière et couleurs équilibrées")
    finally:
        ai_inpaint.upscale_state.update(busy=False, progress=100, step="")
    return out, done


def enhance_data_url(data_url):
    import base64
    import io
    if not ai_inpaint._deps_ok():
        raise RuntimeError("L'IA d'amélioration n'est pas installée.")
    img, done = enhance(ai_inpaint._decode(data_url, "RGB"))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return {"image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), "done": done}

"""Amélioration en un clic, inspirée de Claid.ai « Enhance » : aucun réglage, tout est décidé selon la photo.

Étapes : 1) nettoyage par IA (compression JPEG, bruit, netteté) avec Real-ESRGAN, à taille égale ou ×2
pour les petites photos ; 2) visages restaurés fidèlement (CodeFormer) ; 3) lumière et couleurs
équilibrées façon « HDR léger ». Priorité absolue : un rendu naturel.
"""

import numpy as np

from . import ai_inpaint

SMALL = 1200   # en dessous (plus grand côté), la photo est agrandie ×2 comme sur Claid
LARGE = 3200   # au-dessus, la photo est déjà très détaillée : on ne la nettoie pas par IA (trop long sans carte graphique)
ORIGINAL_SHARE = {"produit": .6, "portrait": .3}   # part de la photo d'origine remélangée après le nettoyage IA (plus haut = plus naturel)


def default_mode():
    """« produit » (luminaires, objets : matières fidèles, rendu naturel) ou « portrait » (réglage historique, visages)."""
    try:
        from . import config
        m = str(config.load().get("enhance_mode", "produit")).lower()
    except Exception:
        m = "produit"
    return m if m in ORIGINAL_SHARE else "produit"


def _progress(p, step):
    ai_inpaint.yield_to_user()
    ai_inpaint.ustate().update(busy=True, progress=int(p), step=step)


def _blur(a, r):
    from PIL import Image, ImageFilter
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0


def light_and_color(img, product=False):
    """Lumière et couleurs naturelles : niveaux prudents, ombres débouchées localement, vibrance douce.

    product=True (photos d'objets) : couleur de la matière intouchée (pas de balance des blancs ni de vibrance),
    HDR local et contraste réduits pour éviter halos et rendu « plastique », grain fin remis à la fin.
    """
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
    if neutral.mean() > .03 and not product:
        m = small[neutral].mean(0)
        gains = np.clip(m.mean() / m, .97, 1.03)
    a = a * gains
    # niveaux + tons moyens (même courbe sur les 3 couches)
    mid_n = np.clip((mid - lo) / max(1e-3, hi - lo), .05, .95)
    gamma = 1 + (np.clip(np.log(.46) / np.log(mid_n), .82, 1.18) - 1) * .5
    if product:
        # produit : la courbe agit sur la luminosité seule et les 3 couches sont mises à l'échelle ensemble,
        # les proportions de couleur (teinte du laiton, du noir mat, du blanc) restent exactement celles de la photo
        l0 = a @ np.array([.299, .587, .114], np.float32)
        l1 = np.clip((l0 - lo) / max(1e-3, hi - lo), 0, 1) ** gamma
        a = np.clip(a * (l1 / np.maximum(l0, 1e-3))[..., None].clip(.5, 2.0), 0, 1)
    else:
        a = np.clip((a - lo) / max(1e-3, hi - lo), 0, 1)
        a = a ** gamma
    # HDR léger : ombres débouchées et hautes lumières retenues, selon la luminosité locale
    lum = a @ np.array([.299, .587, .114], np.float32)
    # luminosité locale calculée sur une image réduite (8× plus rapide), puis ré-agrandie
    from PIL import Image as _I
    k = max(1, min(img.size) // 400)
    lum_small = _I.fromarray((lum * 255).clip(0, 255).astype(np.uint8)).resize((max(1, img.width // k), max(1, img.height // k)), _I.BILINEAR)
    local_small = _blur(np.asarray(lum_small, np.float32) / 255.0, max(2, min(lum_small.size) * .03))
    local = np.asarray(_I.fromarray((local_small * 255).astype(np.uint8)).resize(img.size, _I.BILINEAR), np.float32) / 255.0
    sh, hl = (.08, .06) if product else (.22, .08)
    gain = 1 + sh * np.clip(.42 - local, 0, .42) / .42 - hl * np.clip(local - .78, 0, .22) / .22
    a = a * gain[..., None]
    # contraste doux (courbe en S très légère) et vibrance modérée, peau protégée
    a = np.clip(a, 0, 1)
    a = a + (a * a * (3 - 2 * a) - a) * (.05 if product else .12)
    lum = a @ np.array([.299, .587, .114], np.float32)
    sat = a.max(2) - a.min(2)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    skin = (r > g) & (g > b) & (r - b > .06) & (r - b < .5)
    k = 1 + (0 if product else .10) * (1 - sat) ** 2 * np.where(skin, .25, 1)
    a = lum[..., None] + (a - lum[..., None]) * k[..., None]
    if product:   # grain fin et régulier : casse l'aspect lissé laissé par le nettoyage IA
        a = a + np.random.default_rng(7).normal(0, 1.2 / 255, a.shape[:2]).astype(np.float32)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))


def pro_tone(img, crisp=.2):
    """Lumière et couleurs « photo de studio », pour les photos produit :
    blancs vraiment blancs (balance des blancs prudente prise sur les zones neutres claires), exposition qui fait
    respirer la photo sans brûler les hautes lumières, tons moyens posés, contraste doux, « clarté » qui fait
    ressortir les matières, et piqué de sortie fin. Les teintes des matières sont conservées (toutes les
    corrections passent par la luminosité, sauf la balance des blancs)."""
    from PIL import Image, ImageFilter
    W = np.array([.299, .587, .114], np.float32)
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    sm = np.asarray(img.convert("RGB").resize((max(8, img.width // 4), max(8, img.height // 4))), np.float32) / 255.0
    lum_s = sm @ W
    # 1. balance des blancs : zones claires et peu colorées (fond, murs, blancs) ramenées vers le neutre, sans excès
    sat_s = sm.max(2) - sm.min(2)
    neutral = (sat_s < .14) & (lum_s > .45) & (lum_s < .98)
    if neutral.mean() > .04:
        m = sm[neutral].mean(0)
        # prudente : une dérive de couleur est corrigée, mais l'ambiance chaude d'une lampe allumée est gardée
        gains = np.clip(1 + (m.mean() / m - 1) * .45, .975, 1.025)
        a = a * gains
        sm = sm * gains
        lum_s = sm @ W
    # 2. exposition et niveaux (sur la luminosité) : point blanc vers 0,97, noirs jamais bouchés
    lo, hi, mid = np.percentile(lum_s, [0.3, 99.6, 50])
    lo = min(lo, .12) * .5
    hi = max(hi, .55)
    l0 = a @ W
    l1 = np.clip((l0 - lo) / max(1e-3, hi - lo) * .97, 0, 1)
    # 3. tons moyens : médiane amenée doucement vers 0,48
    mid_n = np.clip((mid - lo) / max(1e-3, hi - lo) * .97, .05, .95)
    gamma = 1 + (np.clip(np.log(.48) / np.log(mid_n), .8, 1.2) - 1) * .45
    l1 = l1 ** gamma
    # 4. contraste doux (courbe en S légère)
    l1 = l1 + (l1 * l1 * (3 - 2 * l1) - l1) * .08
    # 5. clarté : contraste local à grand rayon, matières et volumes qui ressortent (sans halo : effet plafonné)
    r = max(4, max(img.size) / 90)
    L = Image.fromarray((np.clip(l1, 0, 1) * 255).astype(np.uint8))
    base = np.asarray(L.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255
    l1 = l1 + np.clip(l1 - base, -.06, .06) * .22
    # 6. piqué de sortie fin (petit rayon, seuil : le bruit et le grain du fond ne sont pas accentués)
    L = Image.fromarray((np.clip(l1, 0, 1) * 255).astype(np.uint8))
    fine = l1 - np.asarray(L.filter(ImageFilter.GaussianBlur(max(.7, max(img.size) / 2200))), np.float32) / 255
    l1 = l1 + np.where(np.abs(fine) > 4 / 255, fine, 0) * crisp
    l1 = np.clip(l1, 0, 1)
    a = a * (l1 / np.maximum(l0, 1e-3)).clip(.4, 2.5)[..., None]
    # 7. vibrance très légère sur les couleurs ternes uniquement (les couleurs déjà vives ne bougent pas)
    lum = a @ W
    sat = a.max(2) - a.min(2)
    a = lum[..., None] + (a - lum[..., None]) * (1 + .08 * np.clip(1 - sat * 3, 0, 1))[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))


def enhance(img, best=False, mode=None, sharp=False):
    """Renvoie (image améliorée, liste des étapes réalisées). best=True : qualité maximale (plus lent).
    mode : « produit » (défaut, voir default_mode) ou « portrait »."""
    from PIL import Image
    from . import ai_face
    img = img.convert("RGB")
    mode = mode or default_mode()
    product = mode == "produit"
    keep = ORIGINAL_SHARE[mode]
    w, h = img.size
    done = []
    quality = "max" if best and ai_inpaint.pack_ready("upmax") else "fast"
    if sharp:   # netteté renforcée : moins de photo d'origine remélangée ; modèle le plus fin en qualité maximale
        quality, keep = ("sharpmax" if best and ai_inpaint.pack_ready("sharp") else "sharp"), keep * .5
    if product and not best:
        # moteur « naturel » (2xNomosUni) + lumière et couleurs de studio : rendu photo, matières fidèles
        try:
            if max(w, h) < SMALL:
                _progress(2, "Nettoyage et agrandissement ×2…")
                out = ai_inpaint.natural_x2(img, (2, 85))
                done.append(f"agrandie ×2 ({out.width}×{out.height})")
            elif w * h <= 5_000_000:
                # nettoyage à pleine définition : l'IA travaille en ×2 puis l'image revient à sa taille (aucun détail perdu)
                _progress(2, "Nettoyage de la photo par l'IA…")
                out = ai_inpaint.natural_x2(img, (2, 85)).resize((w, h), Image.LANCZOS)
            elif max(w, h) <= LARGE:
                _progress(2, "Nettoyage de la photo par l'IA…")
                half = img.resize((w // 2, h // 2), Image.LANCZOS)
                out = Image.blend(ai_inpaint.natural_x2(half, (2, 85)).resize((w, h), Image.LANCZOS), img, .35)
            else:
                out = img
                done.append("photo déjà en haute résolution : nettoyage IA non nécessaire")
            if out is not img:
                done.append("compression et bruit nettoyés, matières et détails conservés")
            _progress(90, "Lumière et couleurs…")
            out = pro_tone(out, crisp=.35 if sharp else .2)
            done.append("lumière et couleurs de studio (blancs nets, matières mises en valeur)")
            return out, done
        finally:
            ai_inpaint.ustate().update(busy=False, progress=100, step="")
    try:
        # 1. nettoyage et netteté par IA
        if max(w, h) < SMALL:
            _progress(2, "Nettoyage de la photo par l'IA…")
            out = ai_inpaint.upscale_image(img, 2, quality=quality)
            done.append(f"agrandie ×2 ({out.width}×{out.height})")
            done.append("compression et bruit nettoyés, netteté " + ("renforcée" if sharp else "restaurée"))
        elif max(w, h) <= LARGE:
            _progress(2, "Nettoyage de la photo par l'IA…")
            if sharp:
                half = img.resize((w // 2, h // 2), Image.LANCZOS)
                clean = ai_inpaint.upscale_image(half, 4, quality=quality).resize((w, h), Image.LANCZOS)
                out = Image.blend(clean, img, keep)
            elif quality == "max":
                # qualité max : le grand modèle travaille sur la photo réduite de moitié et la ramène à sa taille
                # (4× moins de calcul qu'un ×2 suivi d'une réduction, pour un rendu équivalent)
                half = img.resize((w // 2, h // 2), Image.LANCZOS)
                clean = ai_inpaint.upscale_image(half, 2, quality="max").resize((w, h), Image.LANCZOS)
                out = Image.blend(clean, img, keep)
            else:
                # rapide : l'IA travaille sur la photo réduite de moitié, puis on recombine avec l'original
                half = img.resize((w // 2, h // 2), Image.LANCZOS)
                clean = ai_inpaint.upscale_image(half, 4, quality="fast").resize((w, h), Image.LANCZOS)
                out = Image.blend(clean, img, keep)
            done.append("compression et bruit nettoyés, netteté " + ("renforcée" if sharp else "restaurée"))
        else:
            out = img
            done.append("photo déjà en haute résolution : nettoyage IA non nécessaire")
        # 2. visages
        if not product and ai_inpaint.pack_ready("faces"):
            _progress(75, "Restauration des visages…")
            out, n = ai_face.restore(out, strength=.6, fidelity=1.0)
            if n:
                done.append(f"{n} visage{'s' if n > 1 else ''} restauré{'s' if n > 1 else ''}")
        # 3. lumière et couleurs
        _progress(90, "Lumière et couleurs…")
        out = pro_tone(out, crisp=.3) if product else light_and_color(out, product)
        done.append("lumière et couleurs de studio" if product else "lumière et couleurs équilibrées")
    finally:
        ai_inpaint.ustate().update(busy=False, progress=100, step="")
    return out, done


def enhance_data_url(data_url, best=False, sharp=False):
    import base64
    import io
    if not ai_inpaint._deps_ok():
        raise RuntimeError("L'IA d'amélioration n'est pas installée.")
    img, done = enhance(ai_inpaint._decode(data_url, "RGB"), best, sharp=sharp)
    buf = io.BytesIO()
    img.save(buf, "PNG", compress_level=1)  # encodage rapide (le fichier final est encodé à l'export)
    return {"image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(), "done": done}

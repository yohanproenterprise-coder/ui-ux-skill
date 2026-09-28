"""Export propre des photos du Studio : encodage soigné par Pillow, profil de couleurs, infos de la photo."""

import base64
import io
import re
from pathlib import Path

GPS_TAG, ORIENTATION_TAG = 0x8825, 0x0112


def _srgb_icc():
    try:
        from PIL import ImageCms
        return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    except Exception:
        return None


def _source_exif(source_path=None, source_data=None, keep_gps=False):
    """Récupère les infos de la photo d'origine (date, appareil…), orientation remise à zéro."""
    from PIL import Image
    try:
        if source_path:
            src = Image.open(source_path)
        elif source_data:
            src = Image.open(io.BytesIO(base64.b64decode(source_data.split(",", 1)[-1])))
        else:
            return None
        exif = src.getexif()
        if not exif:
            return None
        exif[ORIENTATION_TAG] = 1  # l'image exportée est déjà dans le bon sens
        if not keep_gps and GPS_TAG in exif:
            del exif[GPS_TAG]
        return exif.tobytes()
    except Exception:
        return None


def encode(png_data_url, fmt="jpeg", quality=92, source_path=None, source_data=None, keep_meta=True, keep_gps=False):
    """Reçoit l'image finale du Studio (PNG, sans perte) et renvoie (octets, extension)."""
    from PIL import Image
    img = Image.open(io.BytesIO(base64.b64decode(png_data_url.split(",", 1)[1])))
    return encode_image(img, fmt, quality, source_path, source_data, keep_meta, keep_gps)


def encode_image(img, fmt="jpeg", quality=92, source_path=None, source_data=None, keep_meta=True, keep_gps=False):
    """Encode une image PIL avec soin (profil sRGB, infos de la photo d'origine) → (octets, extension)."""
    from PIL import Image
    fmt = {"image/jpeg": "jpeg", "image/png": "png", "image/webp": "webp", "jpg": "jpeg"}.get(fmt, fmt)
    if fmt == "jpeg" and img.mode != "RGB":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.getchannel("A") if "A" in img.getbands() else None)
        img = bg
    opts = {}
    icc = _srgb_icc()
    if icc:
        opts["icc_profile"] = icc  # les couleurs s'affichent pareil partout
    exif = _source_exif(source_path, source_data, keep_gps) if keep_meta else None
    if exif:
        opts["exif"] = exif
    buf = io.BytesIO()
    q = int(quality)
    if fmt == "jpeg":
        # 4:4:4 = couleurs nettes sur les contours (les navigateurs utilisent 4:2:0) ; encodage optimisé
        img.save(buf, "JPEG", quality=q, subsampling=0 if q >= 85 else 2, optimize=True, progressive=True, **opts)
        ext = "jpg"
    elif fmt == "webp":
        img.save(buf, "WEBP", quality=q, method=6, **opts)
        ext = "webp"
    else:
        img.save(buf, "PNG", optimize=True, **opts)
        ext = "png"
    return buf.getvalue(), ext


def safe_stem(name):
    return re.sub(r"[^\w\-. ]+", "_", Path(name or "photo").stem)[:80] or "photo"

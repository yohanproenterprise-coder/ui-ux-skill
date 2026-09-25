"""Retouche photo pour l'agent (Pillow, installé automatiquement au premier usage)."""

import glob
import os
import subprocess
import sys
from pathlib import Path

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
FILTERS = ["noir_et_blanc", "sepia", "vintage", "vif", "chaud", "froid", "cinema", "dramatique"]


def ensure_pillow():
    try:
        import PIL  # noqa: F401
        return None
    except ImportError:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "pillow"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return "Impossible d'installer Pillow : " + (r.stderr or r.stdout)[-400:]
        import site
        import importlib
        sys.path.append(site.getusersitepackages())
        importlib.invalidate_caches()
        return None


def _targets(path):
    p = Path(path)
    if p.is_dir():
        return sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXT)
    if any(c in str(path) for c in "*?"):
        return sorted(Path(f) for f in glob.glob(str(path)) if Path(f).suffix.lower() in IMAGE_EXT)
    return [p]


def _ratio_crop(img, ratio):
    w, h = img.size
    a, b = (float(x) for x in ratio.replace("/", ":").split(":"))
    target = a / b
    if w / h > target:
        nw = int(h * target)
        return img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = int(w / target)
    return img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))


def _filter(img, name):
    from PIL import Image, ImageEnhance, ImageOps
    if name == "noir_et_blanc":
        return ImageOps.grayscale(img).convert("RGB")
    if name == "sepia":
        g = ImageOps.grayscale(img)
        return ImageOps.colorize(g, (40, 26, 13), (255, 240, 205), mid=(170, 125, 80))
    if name == "vintage":
        img = ImageEnhance.Color(img).enhance(0.7)
        img = ImageEnhance.Contrast(img).enhance(0.9)
        return Image.blend(img, Image.new("RGB", img.size, (240, 200, 150)), 0.12)
    if name == "vif":
        return ImageEnhance.Contrast(ImageEnhance.Color(img).enhance(1.4)).enhance(1.1)
    if name in ("chaud", "froid"):
        r, g, b = img.split()
        k = 1.08 if name == "chaud" else 0.92
        r = r.point(lambda v: min(255, int(v * k)))
        b = b.point(lambda v: min(255, int(v / k)))
        return Image.merge("RGB", (r, g, b))
    if name == "cinema":
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Color(img).enhance(0.85)
        return Image.blend(img, Image.new("RGB", img.size, (20, 60, 80)), 0.08)
    if name == "dramatique":
        img = ImageEnhance.Contrast(img).enhance(1.35)
        return ImageEnhance.Color(img).enhance(0.75)
    raise ValueError(f"Filtre inconnu. Choix : {', '.join(FILTERS)}")


def _vignette(img, strength):
    from PIL import Image, ImageDraw, ImageFilter
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((-w * .15, -h * .15, w * 1.15, h * 1.15), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(w, h) * .12))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(img, Image.blend(img, dark, min(1, strength)), mask)


def _text(img, text, position="bas-droite", size=None, color="#ffffff"):
    from PIL import ImageDraw, ImageFont
    w, h = img.size
    size = int(size or max(14, w * 0.035))
    font = None
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(name, size)
            break
        except OSError:
            pass
    font = font or ImageFont.load_default()
    d = ImageDraw.Draw(img)
    box = d.textbbox((0, 0), text, font=font)
    tw, th, m = box[2] - box[0], box[3] - box[1], int(size * 0.8)
    x = {"gauche": m, "centre": (w - tw) // 2, "droite": w - tw - m}[position.split("-")[-1] if "-" in position else "centre"]
    y = {"haut": m, "centre": (h - th) // 2, "bas": h - th - m}[position.split("-")[0]]
    d.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0))
    d.text((x, y), text, font=font, fill=color)
    return img


def edit(path, brightness=0, contrast=0, saturation=0, sharpness=0, auto=False, filter=None, crop_ratio=None,
         rotate=0, flip=None, max_size=None, blur=0, vignette=0, text=None, text_position="bas-droite",
         output_format=None, quality=90, out_dir=None, suffix="-retouche"):
    """Les réglages vont de -100 à +100 (0 = inchangé). Renvoie un compte rendu."""
    err = ensure_pillow()
    if err:
        return "ERREUR : " + err
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    if filter and filter not in FILTERS:
        return f"ERREUR : filtre inconnu. Choix : {', '.join(FILTERS)}"
    files = [f for f in _targets(path) if not (suffix and f.stem.endswith(suffix))] or _targets(path)
    if not files or not all(f.exists() for f in files):
        return f"ERREUR : aucune image trouvée pour {path}"
    done = []
    for f in files[:500]:
        img = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        if auto:
            img = ImageOps.autocontrast(img, cutoff=1)
            img = ImageEnhance.Color(img).enhance(1.1)
        if crop_ratio:
            img = _ratio_crop(img, crop_ratio)
        if rotate:
            img = img.rotate(-int(rotate), expand=True)
        if flip in ("horizontal", "vertical"):
            img = ImageOps.mirror(img) if flip == "horizontal" else ImageOps.flip(img)
        for amount, enhancer in ((brightness, ImageEnhance.Brightness), (contrast, ImageEnhance.Contrast),
                                 (saturation, ImageEnhance.Color), (sharpness, ImageEnhance.Sharpness)):
            if amount:
                img = enhancer(img).enhance(1 + float(amount) / 100)
        if filter:
            img = _filter(img, filter)
        if blur:
            img = img.filter(ImageFilter.GaussianBlur(float(blur) / 10))
        if vignette:
            img = _vignette(img, float(vignette) / 100)
        if max_size:
            img.thumbnail((int(max_size), int(max_size)), Image.LANCZOS)
        if text:
            img = _text(img, text, text_position)
        fmt = (output_format or f.suffix.lstrip(".")).lower().replace("jpg", "jpeg")
        fmt = fmt if fmt in ("jpeg", "png", "webp") else "jpeg"
        dest_dir = Path(out_dir) if out_dir else f.parent
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{f.stem}{suffix}.{'jpg' if fmt == 'jpeg' else fmt}"
        img.save(dest, fmt.upper(), quality=int(quality), optimize=True)
        done.append(f"{dest} ({img.size[0]}x{img.size[1]}, {os.path.getsize(dest) // 1024} Ko)")
    more = f"\n… et {len(files) - 500} autres non traitées" if len(files) > 500 else ""
    return f"{len(done)} image(s) retouchée(s) — les originaux sont intacts :\n" + "\n".join(done[:30]) + more

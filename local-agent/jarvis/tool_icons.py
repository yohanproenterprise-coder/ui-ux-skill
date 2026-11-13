"""Icônes (.ico) des outils photo de Jarvis, dessinées avec Pillow : carré arrondi en dégradé et pictogramme blanc."""

from pathlib import Path

COLORS = {  # dégradé (haut-gauche → bas-droite) par outil
    "studio": ((56, 198, 244), (192, 76, 253)),
    "ameliorer": ((124, 92, 255), (255, 92, 154)),
    "dossier": ((255, 181, 71), (255, 112, 67)),
    "gomme": ((255, 92, 154), (192, 76, 253)),
    "scene": ((56, 198, 244), (124, 92, 255)),
}


def _glyph(d, tool, S):
    W = (255, 255, 255, 255)
    k = S / 256
    if tool == "studio":      # photo : cadre, montagne et soleil
        d.rounded_rectangle((44 * k, 60 * k, 212 * k, 196 * k), radius=22 * k, outline=W, width=int(14 * k))
        d.polygon([(64 * k, 180 * k), (112 * k, 120 * k), (146 * k, 160 * k), (166 * k, 138 * k), (196 * k, 180 * k)], fill=W)
        d.ellipse((150 * k, 82 * k, 182 * k, 114 * k), fill=W)
    elif tool == "ameliorer":   # grande étincelle et petite étoile
        cx, cy, r, t = 116 * k, 140 * k, 74 * k, 18 * k
        d.polygon([(cx, cy - r), (cx + t, cy - t), (cx + r, cy), (cx + t, cy + t), (cx, cy + r), (cx - t, cy + t),
                   (cx - r, cy), (cx - t, cy - t)], fill=W)
        cx, cy, r, t = 186 * k, 72 * k, 32 * k, 9 * k
        d.polygon([(cx, cy - r), (cx + t, cy - t), (cx + r, cy), (cx + t, cy + t), (cx, cy + r), (cx - t, cy + t),
                   (cx - r, cy), (cx - t, cy - t)], fill=W)
    elif tool == "dossier":   # dossier avec une étincelle
        d.rounded_rectangle((52 * k, 70 * k, 124 * k, 110 * k), radius=12 * k, fill=W)
        d.rounded_rectangle((52 * k, 92 * k, 204 * k, 192 * k), radius=16 * k, fill=W)
        d.rounded_rectangle((70 * k, 112 * k, 186 * k, 116 * k), radius=2 * k, fill=(255, 255, 255, 90))
    elif tool == "gomme":     # gomme inclinée qui efface un trait
        d.polygon([(70 * k, 150 * k), (150 * k, 70 * k), (200 * k, 120 * k), (120 * k, 200 * k)], fill=W)
        d.polygon([(70 * k, 150 * k), (105 * k, 115 * k), (155 * k, 165 * k), (120 * k, 200 * k)], fill=(255, 255, 255, 150))
        d.line((60 * k, 214 * k, 200 * k, 214 * k), fill=W, width=int(10 * k))
    elif tool == "scene":     # suspension allumée : câble, abat-jour, lumière
        d.line((128 * k, 34 * k, 128 * k, 92 * k), fill=W, width=int(8 * k))
        d.polygon([(128 * k, 84 * k), (64 * k, 160 * k), (192 * k, 160 * k)], fill=W)
        d.pieslice((96 * k, 140 * k, 160 * k, 196 * k), 0, 180, fill=(255, 236, 170, 255))
        d.polygon([(70 * k, 168 * k), (186 * k, 168 * k), (220 * k, 224 * k), (36 * k, 224 * k)], fill=(255, 255, 255, 70))


def make(tool, dest):
    from PIL import Image, ImageDraw
    S = 256
    a, b = COLORS[tool]
    grad = Image.new("RGBA", (S, S))
    px = grad.load()
    for y in range(S):
        for x in range(S):
            t = (x + y) / (2 * S - 2)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((8, 8, S - 8, S - 8), radius=58, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(grad, mask=mask)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    _glyph(ImageDraw.Draw(layer), tool, S)
    img.alpha_composite(layer)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return dest

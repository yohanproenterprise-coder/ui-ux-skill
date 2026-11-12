"""Icône de Photo Studio IA (dégradé bleu, objectif photo et étincelle), en .ico multi-tailles."""
import sys
from PIL import Image, ImageDraw

S = 512
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
grad = Image.new("RGBA", (S, S))
for y in range(S):
    t = y / S
    for x in range(0, S):
        u = (x + y) / (2 * S)
        grad.putpixel((x, y), (int(30 + 20 * u), int(120 + 80 * u), int(255 - 20 * t), 255))
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle((16, 16, S - 16, S - 16), radius=110, fill=255)
img.paste(grad, mask=mask)
d = ImageDraw.Draw(img)
c = S // 2
d.ellipse((c - 150, c - 150, c + 150, c + 150), outline=(255, 255, 255, 255), width=34)
d.ellipse((c - 70, c - 70, c + 70, c + 70), fill=(255, 255, 255, 235))
sx, sy = c + 128, c - 128   # étincelle
d.polygon([(sx, sy - 70), (sx + 18, sy - 18), (sx + 70, sy), (sx + 18, sy + 18), (sx, sy + 70),
           (sx - 18, sy + 18), (sx - 70, sy), (sx - 18, sy - 18)], fill=(255, 236, 160, 255))
img.save(sys.argv[1], sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icône :", sys.argv[1])

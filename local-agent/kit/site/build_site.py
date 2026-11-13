"""Fabrique la page de vente : images intégrées dans le fichier (aucun hébergement d'images nécessaire).
Sortie : index.html (page complète à héberger, par ex. Netlify Drop) et apercu.html (aperçu en ligne, non conservé dans le dépôt)."""
import base64
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
page = (HERE / "page.html").read_text(encoding="utf-8")
page = re.sub(r"\{\{([a-z-]+)\}\}", lambda m: "data:image/jpeg;base64," + base64.b64encode(
    (HERE / "images" / f"{m.group(1)}.jpg").read_bytes()).decode(), page)
(HERE / "apercu.html").write_text(page, encoding="utf-8")
(HERE / "index.html").write_text('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    + page.replace("<header>", "</head>\n<body>\n<header>", 1) + "\n</body>\n</html>\n", encoding="utf-8")
print("ok", len(page) // 1024, "Ko")

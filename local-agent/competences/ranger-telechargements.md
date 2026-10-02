# Ranger un dossier (par défaut Téléchargements) en sous-dossiers par type de fichier

Dossier par défaut : %USERPROFILE%\Downloads (ou celui indiqué par l'utilisateur).

## 1. Aperçu (aucune modification)
Avec run_python, compte les fichiers par catégorie et montre le résultat à l'utilisateur :
- Images : .jpg .jpeg .png .gif .webp .heic .bmp .svg
- Documents : .pdf .doc .docx .odt .txt .rtf .md
- Tableurs : .xls .xlsx .csv .ods
- Présentations : .ppt .pptx .odp
- Vidéos : .mp4 .mkv .avi .mov .webm
- Musique : .mp3 .wav .flac .m4a .ogg
- Archives : .zip .rar .7z .tar .gz
- Installateurs : .exe .msi
- Autres : tout le reste
Ne touche jamais aux sous-dossiers existants ni aux téléchargements en cours (.crdownload .part .tmp).
Demande confirmation avant de déplacer.

## 2. Rangement
Utilise run_python avec ce modèle :

```python
import os, shutil, csv, datetime
from pathlib import Path
src = Path(os.path.expandvars(r"%USERPROFILE%\Downloads"))
cats = {"Images": ".jpg .jpeg .png .gif .webp .heic .bmp .svg", "Documents": ".pdf .doc .docx .odt .txt .rtf .md",
        "Tableurs": ".xls .xlsx .csv .ods", "Présentations": ".ppt .pptx .odp",
        "Vidéos": ".mp4 .mkv .avi .mov .webm", "Musique": ".mp3 .wav .flac .m4a .ogg",
        "Archives": ".zip .rar .7z .tar .gz", "Installateurs": ".exe .msi"}
ext2cat = {e: c for c, exts in cats.items() for e in exts.split()}
log = src / f"journal-rangement-{datetime.datetime.now():%Y%m%d-%H%M%S}.csv"
moved = 0
with open(log, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["avant", "apres"])
    for p in src.iterdir():
        if not p.is_file() or p.suffix.lower() in (".crdownload", ".part", ".tmp") or p == log:
            continue
        dest_dir = src / ext2cat.get(p.suffix.lower(), "Autres")
        dest_dir.mkdir(exist_ok=True)
        dest, n = dest_dir / p.name, 2
        while dest.exists():
            dest = dest_dir / f"{p.stem} ({n}){p.suffix}"; n += 1
        shutil.move(str(p), str(dest)); w.writerow([p, dest]); moved += 1
print(moved, "fichiers rangés. Journal :", log)
```

## 3. Bilan
Annonce le nombre de fichiers déplacés par catégorie et indique que le journal CSV permet d'annuler
(pour annuler : relire le CSV et remettre chaque fichier à son emplacement « avant »).

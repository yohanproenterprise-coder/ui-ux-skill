# Shorts Maker

URL YouTube → moments clés → clips verticaux 1080x1920 (sous-titres inclus).

```bash
pip install -r requirements.txt   # + ffmpeg installé sur le système
python app.py                     # interface web : http://localhost:5000
python cli.py "https://youtube.com/watch?v=XXXX" -n 5 -l 35   # ou en ligne de commande
```

- Sans clé API : détection par énergie audio + densité de parole + mots d'accroche.
- Avec `ANTHROPIC_API_KEY` (et une transcription disponible) : Claude choisit les meilleurs moments et propose des titres.
- Modes : `blur` (vidéo entière sur fond flouté) ou `crop` (recadrage centré).

⚠️ N'utilise que des vidéos dont tu détiens les droits ou sous licence permissive : reposter le contenu d'autrui
sans autorisation est interdit par YouTube/TikTok et ne sera pas monétisé (contenu non original).

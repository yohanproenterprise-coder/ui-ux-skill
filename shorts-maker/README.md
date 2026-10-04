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

## Erreur « This video is not available »
1. `pip install -U yt-dlp` (YouTube change souvent, une vieille version échoue).
2. Vérifie que la vidéo est publique, non restreinte par pays/âge/live, et se lit dans ton navigateur.
3. Si elle exige une connexion : `export YT_COOKIES_BROWSER=chrome` (ou firefox/edge/safari) avant `python app.py`.
4. Depuis un serveur/VPN/cloud, YouTube bloque souvent les IP : lance l'outil depuis ta machine perso.

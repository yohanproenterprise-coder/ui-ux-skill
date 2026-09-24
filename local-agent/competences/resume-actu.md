# Préparer un résumé de l'actualité du jour

## 1. Collecte
Lis 3 ou 4 de ces flux avec fetch_url (ce sont des flux RSS : titres + résumés) :
- Le Monde, à la une : https://www.lemonde.fr/rss/une.xml
- franceinfo, les titres : https://www.francetvinfo.fr/titres.rss
- BBC World : https://feeds.bbci.co.uk/news/world/rss.xml
- Technologie (Numerama) : https://www.numerama.com/feed/
Si l'utilisateur a des centres d'intérêt dans la mémoire (sport, tech, région…), ajoute un web_search dédié.
Si un flux ne répond pas, passe au suivant ; complète au besoin avec web_search("actualités du jour").

## 2. Sélection
Garde 8 à 10 informations vraiment importantes, sans doublons, réparties par thème :
France, Monde, Économie, Tech & Science, et un thème selon les intérêts de l'utilisateur.

## 3. Rédaction
Pour chaque info : un titre en gras + 2 phrases factuelles et neutres + la source.
Termine par « À surveiller » (1 ou 2 sujets qui vont évoluer).
Enregistre le résumé avec write_file dans actu/AAAA-MM-JJ.md, puis donne-le dans ta réponse.
Si c'est une tâche planifiée, envoie aussi une notification (notify) « Ton résumé de l'actu est prêt ».

## Programmer chaque matin
Si l'utilisateur veut le recevoir tous les jours :
schedule(task="Utilise la compétence resume-actu", when="demain 8:00", repeat="quotidienne", kind="tache")

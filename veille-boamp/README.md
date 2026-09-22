# Veille BOAMP

Script qui récupère chaque jour les appels d'offres publics publiés au
[BOAMP](https://www.boamp.fr) (API officielle et gratuite), garde ceux de ta
niche et les classe par intérêt.

Aucune installation : il faut seulement **Python 3.9+**.

## Lancer la veille

```bash
cd veille-boamp
python3 veille_boamp.py            # les 7 derniers jours, réglages de config.json
python3 veille_boamp.py --jours 2  # seulement les 2 derniers jours
```

Le script produit, dans `resultats/` :

- `rapport.html` : la liste des appels d'offres, à ouvrir dans le navigateur ;
- `appels_offres.csv` : le même contenu, à ouvrir dans Excel ou Google Sheets ;
- `deja_vus.json` : la mémoire des avis déjà vus, pour signaler les **nouveaux** (★).

## Régler la niche (`config.json`)

| Champ | Rôle |
|---|---|
| `niche` | Titre affiché dans le rapport |
| `jours` | Nombre de jours de publications à analyser |
| `mots_cles` | Un avis est retenu s'il contient au moins un de ces mots (accents et majuscules ignorés) |
| `mots_exclus` | Un avis contenant un de ces mots est écarté (ex. « voirie » pour le nettoyage) |
| `departements` | Départements ciblés (liste vide = toute la France) |
| `zone_stricte` | `true` : écarte les avis hors zone · `false` : les garde, mais moins bien classés |
| `delai_min_jours` | Délai de réponse jugé confortable (bonus au score) |

Pour une autre niche, copie `config.json` (ex. `config-btp.json`) et lance
`python3 veille_boamp.py --config config-btp.json`.

## Comment le score est calculé

- +3 par mot-clé trouvé dans l'objet du marché, +1 par mot-clé trouvé seulement dans les catégories ;
- +2 si le marché est dans un département ciblé ;
- +2 si la date limite laisse au moins `delai_min_jours` jours, −3 s'il reste moins de 3 jours.

Sont toujours écartés : les avis d'attribution, les rectificatifs et les annulations,
et les marchés dont la date limite est dépassée.

## Automatiser (tous les matins à 7 h)

Linux ou macOS, avec `crontab -e` :

```
0 7 * * * cd /chemin/vers/veille-boamp && python3 veille_boamp.py --jours 2
```

Sous Windows, crée une tâche dans le Planificateur de tâches qui lance la même commande.

## Tests

```bash
python3 -m unittest discover -s tests
```

Les tests utilisent des avis d'exemple (`tests/exemple_avis.json`) et ne se connectent pas à Internet.
Pour rejouer un export téléchargé : `python3 veille_boamp.py --fichier export.json`.

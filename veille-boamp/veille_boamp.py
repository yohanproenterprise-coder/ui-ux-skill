#!/usr/bin/env python3
"""Veille BOAMP : récupère les appels d'offres publics d'une niche et les classe.

Source : API officielle et gratuite du BOAMP (DILA, via Opendatasoft).
Aucune dépendance externe : Python 3.9+ suffit.

Usage :
    python3 veille_boamp.py                    # utilise config.json
    python3 veille_boamp.py --config autre.json --jours 3
    python3 veille_boamp.py --fichier export.json   # rejouer un export local
"""

import argparse
import csv
import html
import json
import os
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

API_URL = (
    "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/"
    "catalog/datasets/boamp/exports/json"
)
LIEN_AVIS = "https://www.boamp.fr/pages/avis/?q=idweb:%22{}%22"

# Avis qui ne sont pas des marchés ouverts (déjà attribués, rectificatifs...)
NATURES_EXCLUES = ("attribution", "resultat", "rectificatif", "annulation")


# ---------------------------------------------------------------- utilitaires

def normaliser(texte):
    """Minuscules sans accents, pour comparer « Propreté » et « proprete »."""
    texte = unicodedata.normalize("NFD", str(texte or "").lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def en_liste(valeur):
    """Les champs BOAMP sont parfois une liste, parfois une chaîne."""
    if valeur is None:
        return []
    if isinstance(valeur, list):
        return [str(v) for v in valeur if v is not None]
    return [str(valeur)]


def lire_date(valeur):
    if not valeur:
        return None
    try:
        return datetime.fromisoformat(str(valeur)[:10]).date()
    except ValueError:
        return None


# ---------------------------------------------------------------- récupération

def telecharger(jours, timeout=60):
    """Télécharge tous les avis publiés depuis `jours` jours."""
    depuis = (date.today() - timedelta(days=jours)).isoformat()
    params = {
        "where": f"dateparution >= date'{depuis}'",
        "order_by": "dateparution desc",
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    requete = urllib.request.Request(url, headers={"User-Agent": "veille-boamp/1.0"})
    try:
        with urllib.request.urlopen(requete, timeout=timeout) as reponse:
            return json.load(reponse)
    except urllib.error.HTTPError as err:
        sys.exit(f"Erreur API BOAMP ({err.code}) : {err.read()[:300]!r}")
    except urllib.error.URLError as err:
        sys.exit(f"Impossible de joindre l'API BOAMP : {err.reason}")


# ---------------------------------------------------------------- analyse

def analyser(avis, config, aujourd_hui=None):
    """Renvoie l'avis enrichi d'un score, ou None s'il ne correspond pas."""
    aujourd_hui = aujourd_hui or date.today()

    nature = normaliser(avis.get("nature_libelle") or avis.get("nature"))
    if any(n in nature for n in NATURES_EXCLUES):
        return None

    objet = normaliser(avis.get("objet"))
    descripteurs = normaliser(" ".join(en_liste(avis.get("descripteur_libelle"))))
    texte = f"{objet} {descripteurs}"

    if any(normaliser(m) in texte for m in config.get("mots_exclus", [])):
        return None

    mots_objet = [m for m in config["mots_cles"] if normaliser(m) in objet]
    mots_desc = [m for m in config["mots_cles"]
                 if normaliser(m) in descripteurs and m not in mots_objet]
    if not mots_objet and not mots_desc:
        return None

    departements = en_liste(avis.get("code_departement"))
    cibles = [str(d) for d in config.get("departements", [])]
    dans_zone = not cibles or any(d in cibles for d in departements)
    if cibles and not dans_zone and config.get("zone_stricte", True):
        return None

    limite = lire_date(avis.get("datelimitereponse"))
    jours_restants = (limite - aujourd_hui).days if limite else None
    if jours_restants is not None and jours_restants < 0:
        return None

    score = 3 * len(mots_objet) + len(mots_desc)
    if cibles and dans_zone:
        score += 2
    if jours_restants is not None:
        delai_min = config.get("delai_min_jours", 7)
        if jours_restants >= delai_min:
            score += 2
        elif jours_restants < 3:
            score -= 3

    idweb = avis.get("idweb") or ""
    return {
        "score": score,
        "idweb": idweb,
        "objet": avis.get("objet") or "",
        "acheteur": avis.get("nomacheteur") or "",
        "departements": ", ".join(departements),
        "publie_le": str(avis.get("dateparution") or "")[:10],
        "date_limite": limite.isoformat() if limite else "",
        "jours_restants": "" if jours_restants is None else jours_restants,
        "procedure": avis.get("procedure_libelle") or "",
        "mots_trouves": ", ".join(mots_objet + mots_desc),
        "lien": avis.get("url_avis") or LIEN_AVIS.format(idweb),
    }


def filtrer(avis_liste, config, aujourd_hui=None):
    resultats = [r for a in avis_liste if (r := analyser(a, config, aujourd_hui))]
    resultats.sort(key=lambda r: (-r["score"], r["date_limite"] or "9999"))
    return resultats


# ---------------------------------------------------------------- mémoire des avis vus

def marquer_nouveaux(resultats, fichier_vus):
    vus = set()
    if os.path.exists(fichier_vus):
        with open(fichier_vus, encoding="utf-8") as f:
            vus = set(json.load(f))
    for r in resultats:
        r["nouveau"] = r["idweb"] not in vus
    with open(fichier_vus, "w", encoding="utf-8") as f:
        json.dump(sorted(vus | {r["idweb"] for r in resultats}), f)


# ---------------------------------------------------------------- sorties

COLONNES = ["nouveau", "score", "date_limite", "jours_restants", "objet", "acheteur",
            "departements", "procedure", "mots_trouves", "publie_le", "idweb", "lien"]


def ecrire_csv(resultats, chemin):
    # utf-8-sig pour que les accents s'affichent correctement dans Excel
    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        ecrivain = csv.DictWriter(f, fieldnames=COLONNES, delimiter=";",
                                  extrasaction="ignore")
        ecrivain.writeheader()
        for r in resultats:
            ecrivain.writerow({**r, "nouveau": "oui" if r.get("nouveau") else ""})


def ecrire_html(resultats, chemin, niche):
    e = html.escape
    lignes = []
    for r in resultats:
        urgence = ""
        if r["jours_restants"] != "" and r["jours_restants"] < 7:
            urgence = " urgent"
        badge = '<span class="new">Nouveau</span>' if r.get("nouveau") else ""
        meta = " · ".join(filter(None, [r["acheteur"], f"Dép. {r['departements'] or '?'}",
                                        r["procedure"]]))
        lignes.append(f"""
      <article class="carte{urgence}">
        <div class="haut"><span class="score">{r['score']}</span>{badge}
          <span class="delai">{e(r['date_limite'] or 'date limite ?')}
          {f"· J-{r['jours_restants']}" if r['jours_restants'] != "" else ""}</span></div>
        <h2><a href="{e(r['lien'])}" target="_blank" rel="noopener">{e(r['objet'])}</a></h2>
        <p class="meta">{e(meta)}</p>
        <p class="mots">{e(r['mots_trouves'])}</p>
      </article>""")
    genere = datetime.now().strftime("%d/%m/%Y %H:%M")
    contenu = "".join(lignes) or '<p class="vide">Aucun appel d\'offres trouvé.</p>'
    page = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Veille BOAMP – {e(niche)}</title>
<style>
  :root {{ --bg:#f6f7f9; --carte:#fff; --texte:#1a1d23; --doux:#5b6270;
          --accent:#2556d8; --bord:#e3e6eb; --urgent:#c2410c; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#111318; --carte:#1b1e25; --texte:#e8eaee; --doux:#9aa1ad;
            --accent:#7aa2ff; --bord:#2a2e37; --urgent:#fb923c; }} }}
  body {{ margin:0; background:var(--bg); color:var(--texte);
         font:15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width:860px; margin:0 auto; padding:24px 16px; }}
  header p {{ color:var(--doux); margin-top:4px; }}
  .carte {{ background:var(--carte); border:1px solid var(--bord); border-radius:12px;
           padding:16px; margin:12px 0; }}
  .carte.urgent {{ border-left:4px solid var(--urgent); }}
  .haut {{ display:flex; gap:8px; align-items:center; font-size:13px; }}
  .score {{ background:var(--accent); color:#fff; border-radius:999px;
           padding:2px 10px; font-weight:600; }}
  .new {{ border:1px solid var(--accent); color:var(--accent); border-radius:999px;
         padding:1px 8px; }}
  .delai {{ margin-left:auto; color:var(--doux); }}
  .urgent .delai {{ color:var(--urgent); font-weight:600; }}
  h2 {{ font-size:16px; margin:10px 0 4px; }}
  h2 a {{ color:inherit; text-decoration:none; }}
  h2 a:hover {{ color:var(--accent); text-decoration:underline; }}
  .meta, .mots {{ margin:2px 0; color:var(--doux); font-size:13px; }}
  .vide {{ color:var(--doux); }}
</style></head>
<body><main>
  <header><h1>Veille BOAMP – {e(niche)}</h1>
    <p>{len(resultats)} appels d'offres ouverts · généré le {genere}</p></header>
  {contenu}
</main></body></html>"""
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(page)


def afficher(resultats, maximum=15):
    for r in resultats[:maximum]:
        nouveau = "★ " if r.get("nouveau") else "  "
        jours = f"J-{r['jours_restants']}" if r["jours_restants"] != "" else "J-?"
        print(f"{nouveau}[{r['score']:>2}] {jours:>5}  {r['objet'][:70]}")
        print(f"        {r['acheteur'][:50]} · dép. {r['departements']}")
    if len(resultats) > maximum:
        print(f"  … et {len(resultats) - maximum} autres dans le rapport.")


# ---------------------------------------------------------------- main

def main():
    dossier = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Veille des appels d'offres BOAMP")
    parser.add_argument("--config", default=os.path.join(dossier, "config.json"))
    parser.add_argument("--jours", type=int, help="nombre de jours à remonter")
    parser.add_argument("--fichier", help="export JSON local au lieu de l'API")
    parser.add_argument("--sortie", default=os.path.join(dossier, "resultats"))
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    jours = args.jours or config.get("jours", 7)

    if args.fichier:
        with open(args.fichier, encoding="utf-8") as f:
            avis = json.load(f)
    else:
        print(f"Téléchargement des avis BOAMP des {jours} derniers jours…")
        avis = telecharger(jours)
    print(f"{len(avis)} avis analysés.")

    resultats = filtrer(avis, config)
    os.makedirs(args.sortie, exist_ok=True)
    marquer_nouveaux(resultats, os.path.join(args.sortie, "deja_vus.json"))

    csv_path = os.path.join(args.sortie, "appels_offres.csv")
    html_path = os.path.join(args.sortie, "rapport.html")
    ecrire_csv(resultats, csv_path)
    ecrire_html(resultats, html_path, config.get("niche", "ma niche"))

    nouveaux = sum(1 for r in resultats if r["nouveau"])
    print(f"{len(resultats)} appels d'offres retenus ({nouveaux} nouveaux).\n")
    afficher(resultats)
    print(f"\nRapport : {html_path}\nTableur : {csv_path}")


if __name__ == "__main__":
    main()

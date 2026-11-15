# Scène 3D cinématique — boutique multi-produits

Moteur Three.js sans modèle externe : 5 familles de luminaires générées par code, adaptées à chaque fiche produit.

| Famille (`data-model`) | Produits concernés | Réglages |
|---|---|---|
| `table` | Lampes de table, de chevet | matière du socle (travertin, marbre, noyer, céramique), couleur d'abat-jour |
| `pendant` | Suspensions | forme `ball` ou `dome`, couleur |
| `wall` | Appliques | forme `globe` ou `bar` (barre en bois), couleur |
| `chandelier` | Lustres | nombre de têtes (3–14), couleur |
| `flush` | Plafonniers | nombre de têtes (3–12) |

## Installation (thème Online Store 2.0)
1. `assets/cinematic-3d.css` et `assets/cinematic-3d.js` → dossier `assets/` du thème.
2. `sections/cinematic-3d.liquid` → dossier `sections/`.
3. Éditeur de thème → modèle **Produit** → Ajouter une section « Scène 3D cinématique ».

## Fonctionnement par produit
- **Modèle automatique** d'après le type de produit (`Suspension`, `Lampe de table`, `Applique murale`, `Plafonnier`, `Lustre`). On peut le forcer par produit avec les métachamps `custom.model_3d` et `custom.shape_3d`.
- **Options Shopify** : les valeurs de couleur (Noir, Blanc, Or, Cuivre, Bleu, Orange…) deviennent des pastilles qui changent la couleur du modèle 3D **et** la variante / le prix du bouton « Ajouter au panier ». Un nombre de « têtes » dans le nom d'une option change le nombre de têtes du lustre.
- Chaque chapitre a ses cases « Afficher les options » et « Afficher le bouton panier ».

## Limites connues
- Les formes sont des **archétypes** (une suspension boule, une applique, etc.), pas la copie exacte de chaque produit. Pour un rendu fidèle d'un produit phare, exportez un `.glb` depuis Blender et chargez-le avec GLTFLoader.
- L'applique murale est la famille la moins aboutie.
- Testé uniquement dans un aperçu hors Shopify (pas dans un thème réel).

## Le film (hero vidéo)
- `cinema/media/film-hero.mp4` : film de 14 s (1280×720, 1,3 Mo, sans son, boucle propre via fondu au noir) — lustre, suspension, lampe de table (vue éclatée), plafonnier, enchaînés en fondu. Rendu image par image avec le même moteur (`cinema/film.html`).
- `sections/hero-film.liquid` : section « Hero film cinématique ». Téléversez le MP4 dans Shopify (Contenu → Fichiers) puis choisissez-le dans le réglage « Film ».
- Pour un film plus long, en 1080p ou 4K : modifier les plans (`SHOTS`) et la taille de la fenêtre dans le script de rendu, et relancer.

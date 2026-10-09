# Thème « Galerie Lumineuse » — installation

Thème Shopify (Online Store 2.0) complet, dark & chaleureux, orienté conversion.
Fichier à téléverser : `galerie-lumineuse-theme.zip` (ou le dossier `galerie-theme/`).

## 1. Installer SANS toucher à votre boutique en ligne
1. Shopify admin → **Boutique en ligne → Thèmes → Ajouter un thème → Importer un fichier zip**.
2. Choisissez `galerie-lumineuse-theme.zip`. Le thème est ajouté **non publié** : votre site actuel ne change pas.
3. **Personnaliser** → vérifiez l'accueil, une fiche produit, une collection, le panier (desktop + mobile).
4. Quand tout vous convient : **… → Publier**. (Votre ancien thème reste disponible pour revenir en arrière.)

## 2. Réglages à faire (15 min)
| Où | Quoi |
|---|---|
| Navigation | Menus nommés `main-menu` (en-tête) et `footer` (pied de page) |
| Accueil → « Collections / pièces » | Associez vos collections (Salon, Salle à manger, Chambre…) + images |
| Accueil → « Produits vedettes » | Choisissez la collection des 6 à 8 pièces à pousser |
| Paramètres du thème → Panier | Seuil de **livraison offerte** (seulement si c'est réel) + collection de suggestions |
| Fiche produit → « Réassurance » / « Livraison & retours » | Vos vraies conditions de livraison et de retour |
| Accueil → « Avis clients » | De vrais avis uniquement (ou installez Judge.me / Loox : le bloc d'avis s'ajoute sur la fiche produit) |
| Paramètres du thème → Couleurs | Accent, fonds, textes |
| Hero | Désactivez la scène 3D si vous visez une vitesse maximale sur mobile |

## 3. Ce qui est inclus pour convertir
- Fiche produit : options (pastilles de couleur), prix/promo dynamiques, galerie synchronisée avec la variante, boutons Shop Pay / Apple Pay, **barre « Ajouter au panier » collante**, réassurance, accordéons, zone d'avis (apps), produits recommandés.
- **Panier latéral** (AJAX) : barre de progression livraison offerte, suggestions, paiement express.
- Collections : filtres Shopify natifs, tri, cartes avec ajout rapide.
- Recherche prédictive, barre d'annonce rotative, bandeau de réassurance, FAQ, newsletter.
- Hero 3D (lampes cliquables) + curseur de **température de lumière** qui recolore la page.
- SEO : balises Open Graph, données structurées produit, titres/descriptions du thème.
- Accessibilité : navigation clavier, `prefers-reduced-motion`, libellés ARIA.

## 5. Section « Lampe allumée au scroll » — la photo de votre produit s'allume
La photo de **votre produit** (par défaut CUIVRE) est posée sur la page, dans le noir. En défilant :
1. un halo naît du luminaire ; 2. un **rond de lumière grandit** depuis lui et révèle toute la photo ; 3. les 3 premières photos de la fiche produit s'enchaînent ; 4. le nom, le prix et le bouton du produit apparaissent.
- **Produit présenté** : champ « Produit présenté ». Ce sont automatiquement les photos de sa fiche.
- **Position du luminaire** : réglez « horizontale » et « verticale » (en % de la photo) pour que la lumière parte du bon endroit. Les photos carrées sont fondues dans un fond prolongé : le luminaire n'est jamais coupé.
- Fonctionne avec **toutes les photos** (fond clair ou sombre). Les photos « propres », sans texte ni cotes dessinés dessus, donnent le plus bel effet.
- **Mode « Pièce 3D qui s'allume »** : alternative sans photo (4 modèles 3D : tubes, dôme cuivre, globes, couronne).
- Pas de Three.js en mode photo. Avec « réduire les animations », la photo s'affiche allumée, sans défilement piloté.

## 4. Limites connues
- Validé avec Theme Check (0 erreur) et testé en navigateur sur une maquette du balisage ; **à prévisualiser sur votre boutique** avant de publier.
- Les pages « compte client » utilisent les comptes clients nouvelle génération de Shopify (pas de gabarits classiques).
- Polices Google (Cormorant Garamond, Jost) et Three.js (cdnjs) sont chargés depuis des CDN externes.
- Pas de faux avis, stock limité ou compte à rebours : tout ce qui est affiché doit être réel.

## Produits en scroll (accueil)

La page d'accueil utilise la section **Produits en scroll** : chaque produit de la collection choisie (par défaut 3) reçoit sa scène « il sort de la pénombre et s'allume au défilement » avec ses vraies photos, puis sa description juste en dessous. Les autres produits restent en grille classique (section « Produits vedettes »).

- **Choisir les produits** : dans l'éditeur, section « Produits en scroll » → collection. Créez une collection « Mis en avant » et placez-y les produits voulus, dans l'ordre voulu.
- **Photos** : les 3 premières photos de la fiche sont utilisées. Le rendu est conçu pour des photos d'ambiance où le luminaire est allumé ; sur des photos détourées à fond blanc, l'effet est beaucoup moins réussi.
- **Position du luminaire** : réglage global dans la section, ou par produit avec les métadonnées `custom.lamp_x` / `custom.lamp_y` (entiers 0–100).

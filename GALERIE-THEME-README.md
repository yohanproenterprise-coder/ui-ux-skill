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

## 5. Section « Lampe allumée au scroll » (nouveau)
Une pièce plongée dans le noir : en faisant défiler la page, trois suspensions s'allument l'une après l'autre
(scintillement, halo, cônes de lumière, ombres sur la table), la température monte de 2200 K à 3200 K et la caméra avance.
- Ajout : éditeur de thème → page d'accueil → **Ajouter une section → « Lampe allumée au scroll »** (déjà placée après les produits vedettes).
- Réglages : longueur du défilement, températures de départ et d'arrivée, textes de chaque étape (blocs) et moment d'apparition de chaque texte.
- Bouton final : renseignez le lien du dernier bloc (collection ou produit phare).
- Performance : Three.js n'est chargé que lorsque la section approche de l'écran. Sans WebGL, un halo animé léger prend le relais ; avec « réduire les animations » activé, la scène s'affiche allumée, sans défilement piloté.

## 4. Limites connues
- Validé avec Theme Check (0 erreur) et testé en navigateur sur une maquette du balisage ; **à prévisualiser sur votre boutique** avant de publier.
- Les pages « compte client » utilisent les comptes clients nouvelle génération de Shopify (pas de gabarits classiques).
- Polices Google (Cormorant Garamond, Jost) et Three.js (cdnjs) sont chargés depuis des CDN externes.
- Pas de faux avis, stock limité ou compte à rebours : tout ce qui est affiché doit être réel.

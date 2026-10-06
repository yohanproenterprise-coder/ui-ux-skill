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

## 5. Section « Lampe allumée au scroll » — produit CUIVRE
Un produit de votre boutique (par défaut **CUIVRE**, la suspension cuivre poli et marbre) plongé dans le noir :
en défilant, il sort de l'obscurité (luminosité qui monte avec un scintillement, halo ambré, poussière lumineuse, léger travelling),
la température passe de 2200 K à 3200 K, et les 3 premières photos du produit s'enchaînent.
La dernière étape affiche son nom, son prix (« dès 213 € ») et un bouton vers sa fiche.
- Ajout / changement de produit : éditeur de thème → page d'accueil → section « Lampe allumée au scroll » → champ **Produit à révéler**.
- Textes, moments d'apparition, longueur du défilement et températures se règlent dans la section et ses blocs.
- Mode alternatif « Décor 3D générique » (lampes en cuivre ou verre dans une pièce) si aucun produit n'est choisi.
- Léger : pas de Three.js en mode produit (images + un canvas 2D). Avec « réduire les animations », le produit s'affiche allumé, sans défilement piloté.
- Les photos sont celles de la fiche produit : plus elles sont sombres et contrastées, plus l'effet est fort.

## 4. Limites connues
- Validé avec Theme Check (0 erreur) et testé en navigateur sur une maquette du balisage ; **à prévisualiser sur votre boutique** avant de publier.
- Les pages « compte client » utilisent les comptes clients nouvelle génération de Shopify (pas de gabarits classiques).
- Polices Google (Cormorant Garamond, Jost) et Three.js (cdnjs) sont chargés depuis des CDN externes.
- Pas de faux avis, stock limité ou compte à rebours : tout ce qui est affiché doit être réel.

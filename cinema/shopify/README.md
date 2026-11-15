# Scène 3D cinématique pour Shopify

Tout est généré par code (Three.js, aucun modèle externe) : luminaire AURA procédural, matières dessinées sur canvas, lumière, poussière, caméra pilotée par le défilement, configurateur de matière/couleur.

## Installer dans un thème Shopify (Online Store 2.0)
1. Copiez `assets/cinematic-3d.css` et `assets/cinematic-3d.js` dans le dossier `assets/` du thème.
2. Copiez `sections/cinematic-3d.liquid` dans `sections/`.
3. Éditeur de thème → Ajouter une section → « Scène 3D cinématique ». Les chapitres, couleurs, longueur du défilement et le produit (bouton panier) se règlent dans l'éditeur.

## Aperçu local
Ouvrez `../index.html` (page autonome utilisant les mêmes fichiers).

## Remplacer par votre vrai produit
Le luminaire est dans la section « le luminaire » de `cinematic-3d.js` (LatheGeometry aux vraies dimensions). Pour un modèle réel : exportez un `.glb` depuis Blender (< 5 Mo, Draco) et chargez-le avec GLTFLoader à la place du groupe `lamp`.

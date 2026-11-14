---
name: animation-3d
description: Build 3D product viewers and animated, cinematic pages with free open-source tools (Three.js, GSAP + ScrollTrigger, Magic UI) and check them offline with tools/preview.js. Use for any 3D scene, product in 3D, scroll animation, cinematic hero, or animated landing page in this repository.
---

# 3D et animation, outils gratuits

Stack 100 % gratuite et open source, déjà présente dans le dépôt :

| Besoin | Outil | Où |
|---|---|---|
| 3D (produit, scène, lumière, ombres) | Three.js r147 (MIT) | CDN `https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js` · copie locale `vendor/three/` |
| Rotation à la souris / au doigt | OrbitControls | `.../three@0.147.0/examples/js/controls/OrbitControls.js` |
| Modèle 3D réel (.glb / .gltf) | GLTFLoader | `.../three@0.147.0/examples/js/loaders/GLTFLoader.js` |
| Animations, apparitions au défilement | GSAP 3.12.5 + ScrollTrigger | `https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js` (+ `ScrollTrigger.min.js`) · `vendor/gsap/` |
| Composants animés React | Magic UI (MIT) | skill `magic-ui`, sources dans `.claude/skills/magic-ui/components/` |
| Choix du style, couleurs, polices | ui-ux-pro-max | skill `ui-ux-pro-max` |

Ces URL sont exactement celles que `tools/preview.js` remplace par `vendor/`. Garde ces versions pour que l'aperçu hors ligne marche.

## Règles

- **Une page = un fichier HTML autonome.** CSS écrit à la main avec des variables (`:root`), pas de Tailwind CDN : l'aperçu hors ligne ne peut pas le charger.
- **Produit en 3D sans modèle** : `LatheGeometry` pour les objets ronds (lampes, vases, bols), `ExtrudeGeometry` pour les profils plats. Toujours aux **vraies dimensions** du produit (en cm, lues dans la fiche Shopify).
- **Avec un vrai modèle** : `.glb` chargé par GLTFLoader (format conseillé : glb, < 5 Mo).
- **Matières** : textures dessinées sur `<canvas>` (travertin, bois, marbre…), plus `bumpMap` pour le relief. `MeshStandardMaterial`, `ACESFilmicToneMapping`, `sRGBEncoding`.
- **Lumière d'un luminaire** : `SpotLight` vers le bas avec ombres, plus `PointLight` doux, intérieur de l'abat-jour en `MeshBasicMaterial` qui brille, et halo au sol en plan additif. Teintes : 3000 K `#ffb46b`, 4000 K `#ffd9a8`, 6000 K `#eef2ff`.
- **Animations** :
  - les durées vont de 400 à 1100 ms, avec `expo.out` ;
  - au défilement, seule la position bouge (`y`, `x`, `scale`), jamais une opacité à 0 qui laisserait la page vide au repos ;
  - le titre entre mot par mot.
- **Toujours** respecter `prefers-reduced-motion` (pas de GSAP, pas d'auto-rotation), mettre un texte de repli si la 3D ne charge pas, mettre la 3D en pause hors écran (`IntersectionObserver`), et utiliser `setPixelRatio(min(dpr, 2))`.
- **Téléphone** : la 3D garde une hauteur fixe (`clamp()`), le zoom est désactivé dans les pages (il gênerait le défilement) et la page ne déborde jamais en largeur.

## Vérifier

```bash
node tools/preview.js chemin/page.html /chemin/sortie
```

Le script crée des captures « bureau » et « téléphone » (écran et page complète), et signale les erreurs JavaScript et les débordements en largeur. La 3D est rendue par le processeur (SwiftShader), donc lentement, mais fidèlement.

## Exemple de référence

`roka/index.html` et la lampe ROKA, de La Galerie Lumineuse, en travertin, D15 × H16 cm.

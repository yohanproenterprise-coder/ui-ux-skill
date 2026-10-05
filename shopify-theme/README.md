# La Galerie Lumineuse — sections motion & 3D pour Shopify

Sept sections Online Store 2.0, modifiables depuis l'éditeur de thème, qui utilisent tes vrais produits et collections.

| Section | Rôle |
|---|---|
| `GL · Hero 3D` | Scène Three.js de suspensions lumineuses (balancement, poussière, parallaxe souris) + curseur de **température de lumière** 2200–6500 K qui recolore tout le site |
| `GL · Bandeau défilant` | Marquee infini (catégories, promesses…) |
| `GL · Manifeste` | Texte dont les mots s'allument au scroll |
| `GL · Collection animée` | Produits d'une collection, filtres par type, cartes inclinées en 3D, prix `dès` |
| `GL · Univers (pièces)` | 3 pièces avec images en parallaxe |
| `GL · Chiffres animés` | Compteurs |
| `GL · Appel final` | Bloc de fin avec halo lumineux |

## Installation

### Option A — éditeur de code (sans outil)
1. Boutique en ligne → Thèmes → **… → Dupliquer** (travaille toujours sur une copie) puis **… → Modifier le code**.
2. Dans la copie, crée/colle chaque fichier du dossier :
   - `assets/gl-motion.css`, `assets/gl-motion.js`
   - `snippets/gl-assets.liquid`
   - `sections/gl-*.liquid` (7 fichiers)
3. Éditeur de thème → page d'accueil → **Ajouter une section** → choisis les sections « GL · … ».
   (ou colle `examples/index.json` dans `templates/index.json` pour obtenir la page complète d'un coup — remplace l'accueil existant.)

### Option B — Shopify CLI
```bash
cd shopify-theme
shopify theme push --unpublished --theme "GL motion"   # ou: shopify theme dev
```
Les fichiers doivent être fusionnés dans un thème existant (le dossier ne contient que les ajouts).

## Notes
- Aucun fichier du thème n'est modifié : tout est préfixé `gl-`.
- Polices : Cormorant Garamond + Jost (Google Fonts). Three.js est chargé depuis cdnjs **uniquement** si le hero 3D est actif ; pour héberger en local, dépose `three.min.js` (r128) dans `assets/` et change `THREE_URL` dans `gl-motion.js`.
- `prefers-reduced-motion` est respecté (animations coupées). Sans WebGL, le hero retombe sur un fond simple.
- Pour du texte clair sur fond clair, change les couleurs `Fond` / `Texte` dans chaque section.

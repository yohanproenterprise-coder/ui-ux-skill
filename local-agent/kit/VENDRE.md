# Vendre Photo Studio IA — guide pas à pas

Tout est prêt côté application : page de vente, essai gratuit de 7 jours et clés de licence.
Il reste à ouvrir la boutique Lemon Squeezy, puis à m'envoyer 4 informations pour tout brancher.

## 1. Créer la boutique Lemon Squeezy (≈ 20 min)
1. Crée un compte sur https://www.lemonsqueezy.com puis une boutique (« Store »), par exemple « Photo Studio IA ».
2. Renseigne ton identité et ton moyen de paiement (virement ou PayPal) dans **Settings → Payouts**.
   Lemon Squeezy est « vendeur officiel » (merchant of record) : il encaisse, gère la TVA européenne et te reverse le reste
   (commission d'environ 5 % + 0,50 € par vente).

## 2. Le produit payant
1. **Products → New product** : nom « Photo Studio IA », prix **29 €**, paiement unique.
2. Description : reprends les textes de la page de vente.
3. **Files** : ajoute l'installateur `PhotoStudioIA-Setup-….exe` (à télécharger dans GitHub → Releases → brouillon
   « Photo Studio IA (dernière version) »).
4. **License keys** : active-les, **Activation limit : 2**, **Expires : never**.
5. Publie le produit.

## 3. Le produit « essai gratuit »
1. **New product** : « Photo Studio IA — essai gratuit », prix **0 €**.
2. Même fichier d'installation, **sans** clés de licence.
   Chaque téléchargement de l'essai te donne l'e-mail de la personne : pratique pour la relancer.

## 4. M'envoyer ces 4 informations
| Information | Où la trouver |
|---|---|
| Lien d'achat du produit payant | page du produit → **Share** → lien de paiement (checkout) |
| Lien de l'essai gratuit | même chose sur le produit à 0 € |
| Numéro de la boutique (Store ID) | **Settings → Stores** |
| Numéro du produit payant (Product ID) | dans l'adresse de la page du produit (`…/products/123456`) |

Je branche alors les liens sur la page de vente et j'active la vérification des clés dans l'application
(fichier `licence-config.json`). L'installateur est refabriqué tout seul : remplace ensuite le fichier dans les deux produits.

## 5. Mettre la page de vente en ligne (≈ 2 min, gratuit)
1. Va sur https://app.netlify.com/drop
2. Glisse le fichier `local-agent/kit/site/index.html` dans la page.
3. Netlify te donne une adresse publique. Tu peux y relier un nom de domaine (≈ 10 €/an) dans les réglages du site.

## 6. Avant la première vente
- **Rends le dépôt GitHub privé** (Settings → Change visibility) : sinon le code de l'application est visible de tous.
- **Mentions légales et conditions de vente** : obligatoires en France (nom ou société, SIRET, adresse, e-mail de contact,
  droit de rétractation pour un logiciel téléchargé, garanties). Les liens sont déjà prévus en bas de la page.
- **Photos de la page** : remplace les photos de démonstration (moto, café) par tes propres photos produit, par exemple tes
  luminaires AEVYX avant/après. Les photos de démonstration viennent d'une bibliothèque scientifique libre : leur usage
  commercial n'est pas garanti.
- **Décors créés par l'IA** : vérifie les conditions d'utilisation de Pollinations pour un usage commercial.
- **Avertissement de Windows** : il disparaît avec un certificat de signature de code (≈ 100 à 300 €/an), facultatif au début.

## 7. Les mises à jour
À chaque amélioration, l'installateur est refabriqué automatiquement (GitHub → Releases). Remplace le fichier dans les deux
produits Lemon Squeezy : les acheteurs retrouvent toujours la dernière version dans leur e-mail d'achat.

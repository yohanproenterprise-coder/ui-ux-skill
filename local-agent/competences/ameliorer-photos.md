# Améliorer des photos (comme le bouton ✨ du Studio)

Quand l'utilisateur veut une photo plus nette, plus propre ou plus belle, sans régler quoi que ce soit.

## Une ou quelques photos
Utilise enhance_photo avec le chemin de la photo (ou un motif comme C:\…\*.jpg).
- mode « produit » (par défaut) : objets, bijoux, luminaires, vêtements… matières et couleurs fidèles.
- mode « portrait » : photos de personnes, visages restaurés.
- best=true seulement si l'utilisateur veut la qualité maximale (environ 3× plus lent).
La copie « -amelioree » est créée à côté de l'original, qui reste intact. Donne le chemin du résultat
et propose de l'ouvrir (open_item).

## Un dossier entier
Utilise enhance_folder (en arrière-plan, reprise automatique si Jarvis est fermé, copies dans « Améliorées »).
Pour savoir où ça en est : photo_folder_status.

## Si l'IA n'est pas installée
L'outil le dit : demande à l'utilisateur d'ouvrir le Studio et de cliquer une fois sur « ✨ Améliorer la photo »
pour l'installer (≈ 530 Mo), puis recommence.

# Faire le ménage sur le PC pour libérer de l'espace disque

Règle d'or : ANALYSER et MONTRER d'abord, ne rien supprimer sans accord explicite. Ne jamais toucher à
C:\Windows, C:\Program Files*, ProgramData, ni à AppData (sauf le dossier Temp), ni aux fichiers OneDrive.

## 1. Analyse (aucune modification)
Lance ces commandes avec run_command (PowerShell) :
- Espace libre :
  `Get-PSDrive C | Select-Object @{n='Utilisé (Go)';e={[math]::Round($_.Used/1GB,1)}},@{n='Libre (Go)';e={[math]::Round($_.Free/1GB,1)}}`
- Taille des fichiers temporaires :
  `"{0:N2} Go" -f ((Get-ChildItem $env:TEMP -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum/1GB)`
- Taille de la Corbeille :
  `"{0:N2} Go" -f ((Get-ChildItem 'C:\$Recycle.Bin' -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum/1GB)`
- Les 20 plus gros fichiers du dossier utilisateur :
  `Get-ChildItem $env:USERPROFILE -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch '\\AppData\\|\\OneDrive' } | Sort-Object Length -Descending | Select-Object -First 20 @{n='Go';e={[math]::Round($_.Length/1GB,2)}},LastWriteTime,FullName | Format-Table -AutoSize | Out-String -Width 300`
- Téléchargements non modifiés depuis plus de 90 jours :
  `Get-ChildItem "$env:USERPROFILE\Downloads" -File | Where-Object LastWriteTime -lt (Get-Date).AddDays(-90) | Measure-Object Length -Sum | Select-Object Count,@{n='Go';e={[math]::Round($_.Sum/1GB,2)}}`
- Doublons (Documents, Images, Téléchargements, fichiers > 1 Mo), avec run_python :
  regrouper par taille, puis calculer le hash SHA-256 des fichiers de même taille, et lister les groupes identiques.

## 2. Rapport
Présente un tableau clair : catégorie, taille, gain possible, niveau de risque (aucun / à vérifier).
Demande à l'utilisateur ce qu'il veut nettoyer. Ne propose jamais de supprimer des photos ou documents
personnels sans qu'il les ait vus dans la liste.

## 3. Nettoyage (seulement ce qui a été accepté)
- Fichiers temporaires (sans risque) :
  `Get-ChildItem $env:TEMP -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue`
- Tout autre fichier : l'envoyer à la CORBEILLE (récupérable), jamais de suppression définitive :
  `Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile('CHEMIN', 'OnlyErrorDialogs', 'SendToRecycleBin')`
- Vider la Corbeille uniquement si l'utilisateur le demande explicitement : `Clear-RecycleBin -Force`
- Pour aller plus loin sans risque, proposer d'ouvrir l'outil Windows : open_item("cleanmgr")

## 4. Bilan
Refais la mesure d'espace libre et annonce le gain réel (avant / après).

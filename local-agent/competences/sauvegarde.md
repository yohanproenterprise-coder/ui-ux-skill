# Sauvegarder les fichiers importants sur un disque externe ou une clé USB

## 1. Préparer
- Liste les disques : `Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter,FileSystemLabel,DriveType,@{n='Libre (Go)';e={[math]::Round($_.SizeRemaining/1GB,1)}},@{n='Taille (Go)';e={[math]::Round($_.Size/1GB,1)}} | Format-Table | Out-String`
- Demande sur quel disque sauvegarder (jamais C:). Vérifie qu'il y a assez de place.
- Dossiers par défaut : Documents, Images, Bureau, Vidéos, Musique (demande s'il en faut d'autres).
  Calcule leur taille avant de commencer.

## 2. Copier (sans rien supprimer)
Pour chaque dossier, avec run_command (timeout 3600) :
`robocopy "$env:USERPROFILE\Documents" "X:\Sauvegarde-Jarvis\Documents" /E /XO /R:1 /W:1 /NFL /NDL /NP /XJ`
(/E copie tout, /XO ne recopie pas ce qui est déjà à jour, /XJ évite les boucles.) N'utilise JAMAIS /MIR ni /PURGE :
ils suppriment des fichiers sur la destination.
Les codes de sortie 0 à 7 de robocopy sont des succès ; 8 ou plus = erreurs à signaler.

## 3. Vérifier et conclure
Compare le nombre de fichiers source / destination. Écris X:\Sauvegarde-Jarvis\derniere-sauvegarde.txt avec la
date et le résumé. Propose un rappel pour la prochaine sauvegarde : schedule(task="Rebrancher le disque et refaire la
sauvegarde", when="+30j", kind="rappel").

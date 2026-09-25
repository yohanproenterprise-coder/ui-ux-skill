# Créer un beau document PDF (lettre, facture, attestation, affiche, compte rendu…)

Méthode : écrire le document en HTML soigné, puis le convertir en PDF avec Microsoft Edge (présent sur tout Windows).

## 1. Contenu
Demande les informations manquantes (nom, adresse, date, destinataire, montants…) plutôt que d'inventer.
Pour une lettre officielle française : expéditeur en haut à gauche, destinataire à droite, lieu et date,
« Objet : … », formule d'appel, corps, formule de politesse, signature.
Pour une facture : numéro, date, coordonnées vendeur/client, tableau (désignation, quantité, prix unitaire, total),
total HT, TVA, total TTC (ou mention « TVA non applicable, art. 293 B du CGI » pour un auto-entrepreneur).

## 2. HTML
Écris le fichier avec write_file dans documents/NOM.html. Style recommandé :
```html
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><style>
@page { size: A4; margin: 20mm; }
body { font: 11pt/1.5 "Segoe UI", Arial, sans-serif; color: #1b1f27; }
h1 { font-size: 20pt; margin: 0 0 12pt; } table { width: 100%; border-collapse: collapse; }
th, td { border-bottom: 1px solid #dde1e8; padding: 6pt; text-align: left; } th { background: #f0f2f5; }
.droite { text-align: right; } .total { font-weight: bold; font-size: 13pt; }
</style></head><body> … </body></html>
```

## 3. Conversion en PDF (run_command)
```
$edge = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
$src = (Resolve-Path "documents\NOM.html").Path
& $edge --headless --disable-gpu --no-pdf-header-footer --print-to-pdf-no-header --print-to-pdf="$($src -replace '\.html$','.pdf')" "file:///$($src -replace '\\','/')"
Start-Sleep 3; Get-Item ($src -replace '\.html$','.pdf')
```
Puis ouvre le PDF avec open_item pour que l'utilisateur le vérifie. Propose des corrections.

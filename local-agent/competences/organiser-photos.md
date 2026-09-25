# Organiser les photos par année et par mois (et repérer les doublons)

Dossier par défaut : %USERPROFILE%\Pictures (ou celui indiqué). Ne supprime jamais de photo.

## 1. Aperçu (aucune modification)
Compte les photos et vidéos (.jpg .jpeg .png .heic .webp .mp4 .mov) et leur taille totale.
Pour la date de prise de vue, utilise cette fonction PowerShell (propriété Windows « Prise de vue ») :
```
$shell = New-Object -ComObject Shell.Application
function DatePrise($f) { $d = $shell.Namespace($f.DirectoryName); $i = $d.ParseName($f.Name)
  $t = ($d.GetDetailsOf($i, 12) -replace '[^\d/: ]', '').Trim()
  if ($t) { try { return [datetime]::ParseExact($t, 'dd/MM/yyyy HH:mm', $null) } catch {} }
  return $f.LastWriteTime }
```
Montre à l'utilisateur la répartition par année et demande confirmation.

## 2. Rangement
Structure : Pictures\Rangées\AAAA\MM - Mois\ (ex : 2025\07 - Juillet). Déplace avec Move-Item ; si le nom
existe déjà, ajoute « (2) ». Écris un journal CSV (avant ; après) dans Pictures\Rangées pour pouvoir annuler.
Ignore les sous-dossiers qui ont déjà un nom parlant (ex : « Mariage Julie ») : demande avant de les toucher.

## 3. Doublons
Avec run_python, regroupe par taille puis par SHA-256 : liste les doublons exacts et l'espace qu'ils occupent.
Propose de mettre les copies (pas l'original le plus ancien) à la Corbeille, seulement avec accord.

## 4. Bilan
Nombre de photos rangées par année, doublons trouvés, espace récupérable.

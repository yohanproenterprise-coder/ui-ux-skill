# Installateur de Jarvis pour Windows : Python, Ollama, modèles, raccourcis.
$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
function Step($t) { Write-Host "`n==> $t" -ForegroundColor Cyan }
function RefreshPath { $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User") }
function PythonOk { try { & python -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>$null; return $LASTEXITCODE -eq 0 } catch { return $false } }

Write-Host "Installation de Jarvis, ton agent IA local" -ForegroundColor Green

Step "Python"
if (PythonOk) { Write-Host "Python est déjà installé." }
else {
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  RefreshPath
  if (-not (PythonOk)) { Write-Host "Installe Python depuis https://www.python.org/downloads/ (coche 'Add Python to PATH') puis relance ce script." -ForegroundColor Red; Read-Host "Entrée pour quitter"; exit 1 }
}
python -m pip install --user --quiet --disable-pip-version-check pypdf
Write-Host "Lecture des PDF activée (pypdf)."

Step "Ollama (moteur des modèles locaux)"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
  RefreshPath
}
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  $cand = "$env:LOCALAPPDATA\Programs\Ollama"
  if (Test-Path "$cand\ollama.exe") { $env:Path += ";$cand" }
  else { Write-Host "Installe Ollama depuis https://ollama.com/download puis relance ce script." -ForegroundColor Red; Read-Host "Entrée pour quitter"; exit 1 }
}
# Réglages mémoire pour un PC à 8 Go : cache compressé et attention optimisée
[Environment]::SetEnvironmentVariable("OLLAMA_FLASH_ATTENTION", "1", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_KV_CACHE_TYPE", "q8_0", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "1", "User")
$env:OLLAMA_FLASH_ATTENTION = "1"; $env:OLLAMA_KV_CACHE_TYPE = "q8_0"; $env:OLLAMA_MAX_LOADED_MODELS = "1"
Write-Host "Démarrage d'Ollama (jusqu'à 1 minute)..."
Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
for ($i = 0; $i -lt 30; $i++) {
  try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 2 | Out-Null; Write-Host "Ollama est prêt."; break } catch { Write-Host "." -NoNewline; Start-Sleep 1 }
}

Step "Téléchargement des modèles (environ 6 Go, patience)"
ollama pull qwen3:4b
Write-Host "Modèle de vision (pour voir les images et l'écran) :"
ollama pull qwen2.5vl:3b

Step "Cerveau cloud gratuit (optionnel mais fortement conseillé sur ce PC)"
Write-Host "Un modèle cloud gratuit comme Gemini est BEAUCOUP plus rapide et intelligent que le modèle local."
Write-Host "Si son quota gratuit est épuisé, Jarvis repasse automatiquement en local."
Write-Host "Clé gratuite : https://aistudio.google.com/apikey (connexion avec un compte Google)"
$key = Read-Host "Colle ta clé Gemini (ou appuie sur Entrée pour rester 100% local)"
if ($key.Trim()) { python "$here\agent.py" --set-key gemini $key.Trim() }

Step "Raccourcis sur le Bureau"
$desk = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("$desk\Jarvis.lnk"); $s.TargetPath = "$here\Jarvis.bat"; $s.WorkingDirectory = $here; $s.IconLocation = "shell32.dll,43"; $s.Save()
$s = $ws.CreateShortcut("$desk\Jarvis (terminal).lnk"); $s.TargetPath = "$here\Jarvis-terminal.bat"; $s.WorkingDirectory = $here; $s.IconLocation = "shell32.dll,24"; $s.Save()

Write-Host "`nInstallation terminée ! Double-clique sur 'Jarvis' sur ton Bureau." -ForegroundColor Green
Read-Host "Entrée pour lancer Jarvis maintenant"
Start-Process "$here\Jarvis.bat"

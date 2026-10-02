# Installation de Jarvis en une commande :
#   irm https://raw.githubusercontent.com/yohanproenterprise-coder/ui-ux-skill/refs/heads/claude/quirky-euler-dtsd45/local-agent/bootstrap.ps1 | iex
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$zip = "$env:TEMP\jarvis.zip"
$dest = "$env:USERPROFILE\JarvisApp"
Write-Host "Téléchargement de Jarvis..." -ForegroundColor Cyan
Invoke-WebRequest "https://github.com/yohanproenterprise-coder/ui-ux-skill/archive/refs/heads/claude/quirky-euler-dtsd45.zip" -OutFile $zip
$tmp = "$env:TEMP\jarvis-extract"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Expand-Archive $zip $tmp -Force
$src = Get-ChildItem $tmp -Directory | Select-Object -First 1
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item "$($src.FullName)\local-agent\*" $dest -Recurse -Force
Get-ChildItem $dest -Recurse | Unblock-File
Remove-Item $zip, $tmp -Recurse -Force
Write-Host "Jarvis copié dans $dest" -ForegroundColor Green
powershell -NoProfile -ExecutionPolicy Bypass -File "$dest\install.ps1"

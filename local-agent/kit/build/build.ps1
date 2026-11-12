# Fabrique l'installateur Windows de Photo Studio IA (lancé par GitHub Actions sur une machine Windows).
# Résultat : kit\build\out\PhotoStudioIA-Setup-<version>.exe
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$root  = (Resolve-Path "$PSScriptRoot\..\..").Path          # dossier local-agent
$out   = "$PSScriptRoot\out"
$stage = "$out\PhotoStudioIA"
$ver   = (Select-String -Path "$root\kit\kit.py" -Pattern 'VERSION = "([^"]+)"').Matches[0].Groups[1].Value
Write-Host "== Photo Studio IA $ver"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force $stage | Out-Null

# 1. Python embarqué (aucune installation nécessaire chez l'utilisateur)
$py = "3.11.9"
Invoke-WebRequest "https://www.python.org/ftp/python/$py/python-$py-embed-amd64.zip" -OutFile "$out\python.zip"
Expand-Archive "$out\python.zip" "$stage\runtime"
$pth = (Get-ChildItem "$stage\runtime\python3*._pth")[0].FullName
(Get-Content $pth) -replace '^#\s*import site', 'import site' | Set-Content $pth -Encoding ascii
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile "$out\get-pip.py"
& "$stage\runtime\python.exe" "$out\get-pip.py" --no-warn-script-location
if ($LASTEXITCODE) { throw "pip" }
& "$stage\runtime\python.exe" -m pip install --no-warn-script-location --disable-pip-version-check onnxruntime numpy pillow
if ($LASTEXITCODE) { throw "dépendances" }

# 2. Application : le Studio de Jarvis + le kit (seulement les modules utiles)
New-Item -ItemType Directory -Force "$stage\app\jarvis\models", "$stage\app\kit" | Out-Null
foreach ($m in "__init__", "config", "ai_inpaint", "ai_face", "enhance_ai", "batch", "scene", "photo_export", "gpu", "system", "photo") {
  Copy-Item "$root\jarvis\$m.py" "$stage\app\jarvis\"
}
Copy-Item "$root\jarvis\index.html", "$root\jarvis\studio.js", "$root\jarvis\studio.css", "$root\jarvis\inpaint.js" "$stage\app\jarvis\"
Copy-Item "$root\jarvis\models\upscale-x4.onnx", "$root\jarvis\models\sharp-x4.onnx" "$stage\app\jarvis\models\"
Copy-Item "$root\kit\kit.py", "$root\kit\kit.js", "$root\kit\LICENCES.txt" "$stage\app\kit\"

# 3. Vérification : l'application démarre et améliore une vraie image
$env:JARVIS_HOME = "$out\test-home"
$p = Start-Process "$stage\runtime\python.exe" -ArgumentList "`"$stage\app\kit\kit.py`"", "--no-window" -PassThru -WindowStyle Hidden
try {
  $ok = $false
  for ($i = 0; $i -lt 40 -and -not $ok; $i++) {
    Start-Sleep 1
    try { $null = Invoke-RestMethod "http://127.0.0.1:7870/ping"; $ok = $true } catch {}
  }
  if (-not $ok) { throw "l'application ne démarre pas" }
  $st = Invoke-RestMethod "http://127.0.0.1:7870/ai_status"
  Write-Host "IA prête : $($st.deps) | paquets : $($st.packs | ConvertTo-Json -Compress)"
  $img = & "$stage\runtime\python.exe" -c "import base64,io;from PIL import Image,ImageDraw;im=Image.new('RGB',(320,240),(200,120,60));ImageDraw.Draw(im).ellipse((60,40,260,200),fill=(40,90,200));b=io.BytesIO();im.save(b,'PNG');print('data:image/png;base64,'+base64.b64encode(b.getvalue()).decode())"
  $body = @{ image = $img; sharp = $true } | ConvertTo-Json
  $r = Invoke-RestMethod "http://127.0.0.1:7870/ai_enhance" -Method Post -Body $body -ContentType "application/json"
  if (-not $r.image) { throw "amélioration : $($r.error)" }
  Write-Host "Amélioration OK : $($r.done -join ', ')"
  $page = Invoke-WebRequest "http://127.0.0.1:7870/" -UseBasicParsing
  if ($page.Content -notmatch "Photo Studio IA") { throw "page" }
} finally {
  Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
  Remove-Item Env:\JARVIS_HOME
}
Remove-Item -Recurse -Force "$out\test-home" -ErrorAction SilentlyContinue
Get-ChildItem $stage -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# 4. Icône et lanceur (.exe)
& "$stage\runtime\python.exe" "$PSScriptRoot\make_icon.py" "$out\icon.ico"
$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
& $csc /nologo /target:winexe /r:System.Windows.Forms.dll "/win32icon:$out\icon.ico" "/out:$stage\Photo Studio IA.exe" "$PSScriptRoot\launcher.cs"
if ($LASTEXITCODE) { throw "lanceur" }

# 5. Installateur
$iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { choco install innosetup -y --no-progress | Out-Null }
& $iscc /Q "/DAppVersion=$ver" "/DSrc=$stage" "/DOut=$out" "/DIcon=$out\icon.ico" "$PSScriptRoot\installer.iss"
if ($LASTEXITCODE) { throw "installateur" }
Get-ChildItem "$out\*.exe" | ForEach-Object { Write-Host ("Installateur : {0} ({1:N0} Mo)" -f $_.Name, ($_.Length / 1MB)) }

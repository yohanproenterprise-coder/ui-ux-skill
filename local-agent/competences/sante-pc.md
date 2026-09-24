# Faire un bilan de santé complet du PC et recommander des améliorations

Ne modifie RIEN pendant le bilan : tu observes, puis tu proposes.

## 1. Mesures (run_command, PowerShell)
- Système et mémoire :
  `Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,LastBootUpTime,@{n='RAM libre (Go)';e={[math]::Round($_.FreePhysicalMemory/1MB,1)}},@{n='RAM totale (Go)';e={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}} | Format-List | Out-String`
- Disques et leur état :
  `Get-PhysicalDisk | Select-Object FriendlyName,MediaType,HealthStatus,@{n='Go';e={[math]::Round($_.Size/1GB)}} | Format-Table | Out-String`
  `Get-PSDrive -PSProvider FileSystem | Select-Object Name,@{n='Libre (Go)';e={[math]::Round($_.Free/1GB,1)}},@{n='Utilisé (Go)';e={[math]::Round($_.Used/1GB,1)}} | Format-Table | Out-String`
- Batterie (portable) : génère le rapport puis extrais les capacités avec run_python :
  `powercfg /batteryreport /output "$env:USERPROFILE\Jarvis\batterie.html"`
  (dans le HTML : DESIGN CAPACITY et FULL CHARGE CAPACITY ; usure = 1 - pleine charge / conception)
- Programmes les plus gourmands en mémoire :
  `Get-Process | Sort-Object WS -Descending | Select-Object -First 10 Name,@{n='RAM (Mo)';e={[int]($_.WS/1MB)}} | Format-Table | Out-String`
- Programmes lancés au démarrage :
  `Get-CimInstance Win32_StartupCommand | Select-Object Name,Location | Format-Table | Out-String -Width 200`
- Sécurité (Windows Defender) :
  `Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated,QuickScanAge | Format-List | Out-String`
- Dernières mises à jour Windows :
  `Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID,InstalledOn | Format-Table | Out-String`
- Dernier redémarrage : si LastBootUpTime date de plus de 7 jours, conseille de redémarrer.

## 2. Rapport
Donne une note globale sur 10, puis une section par point avec 🟢 bon / 🟡 à surveiller / 🔴 à traiter :
mémoire, disque (alerte si moins de 15 % libre), état des disques, batterie (alerte si usure > 30 %),
démarrage (alerte si plus de 8 programmes), sécurité, mises à jour.

## 3. Recommandations
3 à 5 actions concrètes, classées par impact. Pour un PC à 8 Go de RAM, pense à : limiter les onglets du
navigateur, désactiver les programmes inutiles au démarrage (Gestionnaire des tâches > Démarrage :
open_item("taskmgr")), libérer de l'espace (compétence menage-pc), redémarrer régulièrement.
Propose d'appliquer celles qui peuvent l'être, une par une, avec l'accord de l'utilisateur.

; Installateur de Photo Studio IA (Inno Setup). Valeurs fournies par build.ps1 : AppVersion, Src, Out, Icon.
#define AppName "Photo Studio IA"
#define AppExe "Photo Studio IA.exe"

[Setup]
AppId={{B1E6A3C2-7F4D-4C1A-9E2B-5D8F0A6C3E71}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
DefaultDirName={localappdata}\Programs\PhotoStudioIA
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir={#Out}
OutputBaseFilename=PhotoStudioIA-Setup-{#AppVersion}
SetupIconFile={#Icon}
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer une icône sur le Bureau"; GroupDescription: "Raccourcis :"

[Files]
Source: "{#Src}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Lancer {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

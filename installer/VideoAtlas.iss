#define MyAppName "VideoAtlas"
#define MyAppVersion "2.4.0"
[Setup]
AppId={{D72A88F2-54E7-47D8-9472-3C31B7127E99}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\VideoAtlas
DefaultGroupName=VideoAtlas
OutputDir=..\installer-output
OutputBaseFilename=VideoAtlas-Setup-2.4.0
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
[Files]
Source: "..\dist\VideoAtlas\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
[Icons]
Name: "{group}\VideoAtlas"; Filename: "{app}\VideoAtlas.exe"
Name: "{autodesktop}\VideoAtlas"; Filename: "{app}\VideoAtlas.exe"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; GroupDescription: "Additional icons:"
[Run]
Filename: "{app}\VideoAtlas.exe"; Description: "Launch VideoAtlas"; Flags: nowait postinstall skipifsilent

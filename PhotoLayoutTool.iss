#define MyAppName "PhotoLayoutTool"
#define MyAppChineseName "证件照排版工具"
#define MyAppVersion "1.1"
#define MyAppPublisher "Photo Layout Tool"
#define MyAppExeName "PhotoLayoutTool.exe"

[Setup]
AppId={{B81A4FA3-0C82-48DF-BC4B-8D28B383D120}
AppName={#MyAppChineseName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppChineseName}
DefaultGroupName={#MyAppChineseName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=PhotoLayoutTool_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
CloseApplications=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: unchecked

[Files]
Source: "dist\PhotoLayoutTool.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppChineseName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppChineseName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppChineseName}"; Flags: nowait postinstall skipifsilent

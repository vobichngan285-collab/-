#define MyAppName "游戏文字助手"
#define MyAppVersion "1.0.0"
#define MyAppExeName "GameTextReader.exe"

[Setup]
AppId={{1867301B-616D-4289-A98C-16E0EA7DB533}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Game Text Reader Project
DefaultDirName={localappdata}\Programs\GameTextReader
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=..\release
OutputBaseFilename=GameTextReader_1.0_Windows_x64_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\GameTextReader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "创建桌面快捷方式"; GroupDescription: "其他选项:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动游戏文字助手"; Flags: nowait postinstall skipifsilent

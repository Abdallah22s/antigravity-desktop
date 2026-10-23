#ifndef MyAppVersion
  #define MyAppVersion "1.2.0"
#endif
#define MyAppName "Antigravity Desktop"

[Setup]
AppId={{42A41B2E-51A5-4705-A2A6-0DF8EF089BBC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Abdallah22s
AppPublisherURL=https://github.com/Abdallah22s
AppSupportURL=https://github.com/Abdallah22s/antigravity-desktop/issues
AppUpdatesURL=https://github.com/Abdallah22s/antigravity-desktop/releases
DefaultDirName={localappdata}\Programs\AntigravityDesktop
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.19041
OutputDir=..\release
OutputBaseFilename=AntigravityDesktop-Setup-{#MyAppVersion}-windows-x64
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\AntigravityDesktop.exe
LicenseFile=..\LICENSE
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
AppMutex=Local\QNIXDev.AntigravityDesktop.Instance
CloseApplications=no
RestartApplications=no
DisableProgramGroupPage=yes
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppName} Installer
VersionInfoCompany=Abdallah22s
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\AntigravityDesktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Only obsolete application-owned Qt payloads from release 1.0.0.
; Never delete the application directory, user data, or external installations.
Type: filesandordirs; Name: "{app}\_internal\PySide6"
Type: filesandordirs; Name: "{app}\_internal\shiboken6"
Type: filesandordirs; Name: "{app}\_internal\PySide6_Essentials-6.11.2.dist-info"
Type: filesandordirs; Name: "{app}\_internal\shiboken6-6.11.2.dist-info"
Type: filesandordirs; Name: "{app}\_internal\ui"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\AntigravityDesktop.exe"; WorkingDir: "{app}"; AppUserModelID: "Abdallah22s.AntigravityDesktop"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\AntigravityDesktop.exe"; WorkingDir: "{app}"; AppUserModelID: "Abdallah22s.AntigravityDesktop"; Tasks: desktopicon

[Run]
Filename: "{app}\AntigravityDesktop.exe"; Description: "Open {#MyAppName}"; Flags: nowait postinstall skipifsilent unchecked

; Uninstall removes this app only. It does not delete external backups, touch
; Antigravity installations, modify saved accounts or revoke credentials.

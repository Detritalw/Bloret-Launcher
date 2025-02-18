; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{YOUR-GUID-HERE}
AppName=Bloret Launcher
AppVersion=1.0
; AppVersion is automatically updated by the VersionInfoVersion directive.
DefaultDirName={pf}\BloretLauncher
DefaultGroupName=Bloret Launcher
OutputBaseFilename=Bloret-Launcher-Setup
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "output\Bloret-Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "output\cmcl\*"; DestDir: "{app}\cmcl"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "output\icons\*"; DestDir: "{app}\icons"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "output\ui\*"; DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Bloret Launcher"; Filename: "{app}\Bloret-Launcher.exe"

[Run]
Filename: "{app}\Bloret-Launcher.exe"; Description: "{cm:LaunchProgram,Bloret Launcher}"; Flags: nowait postinstall skipifsilent

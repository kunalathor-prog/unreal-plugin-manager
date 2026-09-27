; Per-user installer. Rerun the same Setup executable to replace missing/damaged files.
#ifndef AppVersion
  #error AppVersion must be supplied by Build-Windows.ps1
#endif
#ifndef Publisher
  #define Publisher "Publisher not configured"
#endif
#ifndef SupportURL
  #define SupportURL ""
#endif
[Setup]
AppId={{A661FC26-CBB2-421D-94DC-7E5E4A4C9A75}
AppName=Unreal Pipeline Manager
AppVersion={#AppVersion}
AppPublisher={#Publisher}
AppSupportURL={#SupportURL}
DefaultDirName={localappdata}\Programs\UnrealPipelineManager
DefaultGroupName=Unreal Pipeline Manager
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.22000
OutputDir=..\release
OutputBaseFilename=UnrealPipelineManager-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\app\resources\pipeline.ico
UninstallDisplayIcon={app}\UnrealPipelineManager.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=UnrealPipelineManager.exe
RestartApplications=no

[Files]
Source: "..\dist\UnrealPipelineManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Unreal Pipeline Manager"; Filename: "{app}\UnrealPipelineManager.exe"
Name: "{group}\User Guide"; Filename: "{app}\USER_GUIDE.md"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\UnrealPipelineManager.exe"; Description: "Launch Unreal Pipeline Manager"; Flags: nowait postinstall skipifsilent

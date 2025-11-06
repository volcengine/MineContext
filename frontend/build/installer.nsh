; Custom NSIS script for MineContext installer
; Add data directory selection page

!include "LogicLib.nsh"
!include "nsDialogs.nsh"

; Only define installer-specific code when building the installer (not uninstaller)
!ifndef BUILD_UNINSTALLER

; Define custom variables
Var DataDir

; Initialize variables when installer starts
!macro customInit
  ; Try to read existing installation directory from registry
  ReadRegStr $0 HKCU "Software\MineContext" "InstallDirectory"
  ${If} $0 != ""
    StrCpy $INSTDIR $0
  ${EndIf}

  ; Try to read existing data directory from registry
  ReadRegStr $DataDir HKCU "Software\MineContext" "DataDirectory"
  ${If} $DataDir == ""
    ; Set default to AppData\Local\MineContext
    StrCpy $DataDir "$LOCALAPPDATA\MineContext"
  ${EndIf}
!macroend

; Define variables for data directory page
Var DataDirPage
Var DataDirLabel
Var DataDirText
Var DataDirBrowseButton

; Function to create the custom data directory selection page
Function DataDirectoryPage
  nsDialogs::Create 1018
  Pop $DataDirPage

  ${If} $DataDirPage == error
    Abort
  ${EndIf}

  ; Create label with description
  ${NSD_CreateLabel} 0 0 100% 24u "Select where MineContext will store application data (databases, files, cache). The directory requires write permissions."
  Pop $DataDirLabel

  ; Create text input showing current data directory
  ${NSD_CreateText} 0 36u 75% 12u "$DataDir"
  Pop $DataDirText

  ; Create browse button
  ${NSD_CreateButton} 77% 36u 23% 12u "Browse..."
  Pop $DataDirBrowseButton
  ${NSD_OnClick} $DataDirBrowseButton DataDirectoryBrowse

  nsDialogs::Show
FunctionEnd

; Function to handle browse button click
Function DataDirectoryBrowse
  nsDialogs::SelectFolderDialog "Select Data Directory" "$DataDir"
  Pop $0

  ${If} $0 != error
    StrCpy $DataDir $0
    ${NSD_SetText} $DataDirText "$DataDir"
  ${EndIf}
FunctionEnd

; Function called when leaving the data directory page
Function DataDirectoryLeave
  ; Get the text from the input field
  ${NSD_GetText} $DataDirText $DataDir

  ; Validate that directory path is not empty
  ${If} $DataDir == ""
    MessageBox MB_OK|MB_ICONEXCLAMATION "Please select a data directory."
    Abort
  ${EndIf}

  ; Validate that data directory is not the same as installation directory
  ${If} $DataDir == $INSTDIR
    MessageBox MB_OK|MB_ICONEXCLAMATION "Data directory cannot be the same as the installation directory.$\n$\nInstallation Directory: $INSTDIR$\nData Directory: $DataDir$\n$\nPlease choose a different location for application data."
    Abort
  ${EndIf}

  ; Create the directory if it doesn't exist
  CreateDirectory "$DataDir"

  ; Check if we have write permission by creating a test file
  ClearErrors
  FileOpen $0 "$DataDir\.write_test" w
  ${If} ${Errors}
    MessageBox MB_OK|MB_ICONEXCLAMATION "Cannot write to the selected directory. Please choose another location with write permissions."
    Abort
  ${EndIf}
  FileClose $0
  Delete "$DataDir\.write_test"

  ; Save the data directory to registry
  WriteRegStr HKCU "Software\MineContext" "DataDirectory" "$DataDir"
FunctionEnd

!endif ; BUILD_UNINSTALLER

; Add custom page after installation directory selection
!macro customPageAfterChangeDir
  ; Insert the data directory selection page
  Page custom DataDirectoryPage DataDirectoryLeave
!macroend

; Custom NSIS script for MineContext installer
; Add data directory selection page

!include "LogicLib.nsh"
!include "nsDialogs.nsh"

; Define custom variables
Var DataDir
Var DataDirPage
Var DataDirLabel
Var DataDirText
Var DataDirBrowseButton

; Initialize data directory variable when installer starts
!macro customInit
  ; Try to read existing data directory from registry
  ReadRegStr $DataDir HKCU "Software\MineContext" "DataDirectory"
  ${If} $DataDir == ""
    ; Set default to AppData\Local\MineContext
    StrCpy $DataDir "$LOCALAPPDATA\MineContext"
  ${EndIf}
!macroend

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

; Add custom installation page
!macro customInstallMode
  ; Add the data directory selection page after directory selection
  !define MUI_PAGE_CUSTOMFUNCTION_LEAVE DataDirectoryLeave
  !insertmacro MUI_PAGE_DIRECTORY_CUSTOM DataDirectoryPage
!macroend

; Clean up on uninstall
!macro customUnInstall
  ; Read the data directory from registry
  ReadRegStr $DataDir HKCU "Software\MineContext" "DataDirectory"

  ; Ask user if they want to delete the data directory
  ${If} $DataDir != ""
    MessageBox MB_YESNO|MB_ICONQUESTION "Do you want to delete the application data directory?$\n$\nDirectory: $DataDir$\n$\nThis will permanently delete all your data, including databases and files." IDYES deleteData IDNO skipDelete

    deleteData:
      RMDir /r "$DataDir"

    skipDelete:
  ${EndIf}

  ; Remove registry entry
  DeleteRegKey HKCU "Software\MineContext"
!macroend

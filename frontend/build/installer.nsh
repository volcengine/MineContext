!macro customInit
  ; Set default installation directory
  StrCpy $INSTDIR "$LOCALAPPDATA\${PRODUCT_NAME}"
!macroend

!macro customInstallMode
  ; This ensures the installer appends product name to selected directory
  !define MUI_PAGE_CUSTOMFUNCTION_LEAVE DirectoryLeave
!macroend

Function DirectoryLeave
  ; Get the last part of the path
  Push $INSTDIR
  Call GetFileName
  Pop $R0

  ; If the last folder is not the product name, append it
  ${If} $R0 != "${PRODUCT_NAME}"
    StrCpy $INSTDIR "$INSTDIR\${PRODUCT_NAME}"
  ${EndIf}
FunctionEnd

Function GetFileName
  Exch $R0
  Push $R1
  Push $R2

  StrCpy $R2 $R0 1 -1
  ${If} $R2 == "\"
    StrCpy $R0 $R0 -1
  ${EndIf}

  StrCpy $R1 0
  loop:
    IntOp $R1 $R1 - 1
    StrCpy $R2 $R0 1 $R1
    ${If} $R2 == "\"
      IntOp $R1 $R1 + 1
      StrCpy $R0 $R0 "" $R1
      Goto done
    ${ElseIf} $R2 == ""
      Goto done
    ${EndIf}
    Goto loop
  done:

  Pop $R2
  Pop $R1
  Exch $R0
FunctionEnd


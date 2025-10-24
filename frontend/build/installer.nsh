!macro customInstall
!macroend

!macro customHeader
  !system "echo '' > ${BUILD_RESOURCES_DIR}/customHeader"
!macroend

Var StdInstDir

!macro preInit
  StrCpy $StdInstDir "$LOCALAPPDATA\${PRODUCT_NAME}"
!macroend

!macro customInstallMode
  ; Override the directory page to automatically append product name
  !define MUI_PAGE_CUSTOMFUNCTION_LEAVE CustomDirectoryLeave
!macroend

Function CustomDirectoryLeave
  ; Check if the user selected a directory that doesn't end with product name
  ${GetFileName} $INSTDIR $R0
  ${If} $R0 != "${PRODUCT_NAME}"
    StrCpy $INSTDIR "$INSTDIR\${PRODUCT_NAME}"
  ${EndIf}
FunctionEnd

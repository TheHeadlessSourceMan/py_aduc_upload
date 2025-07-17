;--------------------------------
; py_aduc_upload_setup.nsi
; NSIS installer script for py_aduc_upload with component selection,
; file association, and context menu integration.
;--------------------------------

!include "MUI2.nsh"

Name "Py ADuC Uploader"
OutFile "dist\py_aduc_upload_setup.exe"
InstallDir "$PROGRAMFILES64\py_aduc_upload"
RequestExecutionLevel admin

;--------------------------------
; Installer Pages

!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Components

Section "Uploader" SecUploader
  SetOutPath $INSTDIR\Uploader
  File /r "dist\Uploader\*"
SectionEnd

Section "Octopus" SecOctopus
  SetOutPath $INSTDIR\Octopus
  File /r "dist\Octopus\*"
SectionEnd

Section "Supporting Files" SecSupport
  SectionIn RO
  SetOutPath $INSTDIR\py_aduc_upload
  File /r "py_aduc_upload\*"
SectionEnd

;--------------------------------
; Set default component selections

Function .onInit
  ; Uploader selected by default
  SectionSetFlags ${SecUploader} 1
  ; Octopus NOT selected by default
  ClearSection ${SecOctopus}
FunctionEnd

;--------------------------------
; File Associations and Context Menus

Var /GLOBAL ASSOC_EXT
Var /GLOBAL ASSOC_INDEX

Function RegisterFileTypes
  Push $R0
  Push $R1
  Push $R2
  StrCpy $ASSOC_INDEX 0
  ${DoWhile} $ASSOC_INDEX < 3
    ${If} $ASSOC_INDEX == 0
      StrCpy $ASSOC_EXT ".hex"
    ${ElseIf} $ASSOC_INDEX == 1
      StrCpy $ASSOC_EXT ".elf"
    ${Else}
      StrCpy $ASSOC_EXT ".bin"
    ${EndIf}

    ; ProgID unique per extension
    StrCpy $R0 "pyaducupload$ASSOC_EXT"
    WriteRegStr HKCR "$ASSOC_EXT" "" "$R0"
    WriteRegStr HKCR "$R0" "" "Py ADuC Upload $ASSOC_EXT File"
    WriteRegStr HKCR "$R0\DefaultIcon" "" "$INSTDIR\Uploader\Uploader.exe,0"
    WriteRegStr HKCR "$R0\shell\open\command" "" '"$INSTDIR\Uploader\Uploader.exe" "%1"'

    ; Context menu: Upload with Uploader
    WriteRegStr HKCR "$R0\shell\Upload with Uploader" "" "Upload with Uploader"
    WriteRegStr HKCR "$R0\shell\Upload with Uploader\command" "" '"$INSTDIR\Uploader\Uploader.exe" "%1"'
    WriteRegStr HKCR "$R0\shell\Upload with Uploader" "Icon" "$INSTDIR\Uploader\Uploader.exe,0"

    ; Context menu: Open with Octopus (if installed)
    IfFileExists "$INSTDIR\Octopus\Octopus.exe" 0 +3
      WriteRegStr HKCR "$R0\shell\Open with Octopus" "" "Open with Octopus"
      WriteRegStr HKCR "$R0\shell\Open with Octopus\command" "" '"$INSTDIR\Octopus\Octopus.exe" "%1"'
      WriteRegStr HKCR "$R0\shell\Open with Octopus" "Icon" "$INSTDIR\Octopus\Octopus.exe,0"

    IntOp $ASSOC_INDEX $ASSOC_INDEX + 1
  ${Loop}
  Pop $R2
  Pop $R1
  Pop $R0
FunctionEnd

Section -PostInstall
  Call RegisterFileTypes
SectionEnd

;--------------------------------
; Uninstaller

Section "Uninstall"
  ; Remove installed files
  Delete "$INSTDIR\Uploader\Uploader.exe"
  Delete "$INSTDIR\Octopus\Octopus.exe"
  RMDir /r "$INSTDIR\Uploader"
  RMDir /r "$INSTDIR\Octopus"
  RMDir /r "$INSTDIR\py_aduc_upload"
  ; Remove registry file associations and context menus
  DeleteRegKey HKCR ".hex"
  DeleteRegKey HKCR ".elf"
  DeleteRegKey HKCR ".bin"
  DeleteRegKey HKCR "pyaducupload.hex"
  DeleteRegKey HKCR "pyaducupload.elf"
  DeleteRegKey HKCR "pyaducupload.bin"
  DeleteRegKey /ifempty HKCU "Software\py_aduc_upload"
  Delete "$INSTDIR\uninstall.exe"
  RMDir /r "$INSTDIR"
SectionEnd

;--------------------------------
; Installer Shortcuts (optional)

Section -AdditionalShortcuts
  ; Uploader shortcut
  CreateShortCut "$DESKTOP\Py ADuC Uploader.lnk" "$INSTDIR\Uploader\Uploader.exe"
  ; Octopus shortcut (if installed)
  IfFileExists "$INSTDIR\Octopus\Octopus.exe" 0 +2
    CreateShortCut "$DESKTOP\Octopus.lnk" "$INSTDIR\Octopus\Octopus.exe"
SectionEnd

;--------------------------------

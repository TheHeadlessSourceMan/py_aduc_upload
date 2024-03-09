;--------------------------------
;General information

!include "MUI2.nsh"

!define MUI_ICON "octopus.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "octopus.bmp"
!define MUI_HEADERIMAGE_RIGHT

Unicode true

;The name of the installer
Name "Py ADuC Uploader"

;The output file path of the installer to be created
OutFile "dist\py_aduc_upload_setup.exe"

;The default installation directory
InstallDir "$PROGRAMFILES64\py_aduc_upload"

;Request application privileges for user level privileges
RequestExecutionLevel admin

;--------------------------------
;Installer pages

;Show a page where the user can customize the install directory
Page directory
;Show a page where the progress of the install is listed
Page instfiles


;--------------------------------
;Installer Components

;A section for each component that should be installed
Section "Octopus"

  ;Set output path to the installation directory
  SetOutPath $INSTDIR

  ;Now you can list files that should be extracted to this output path or create
  ;directories:

  File /r "dist\Octopus\*"

SectionEnd

;A section for each component that should be installed
Section "Uploader"

  ;Set output path to the installation directory
  SetOutPath $INSTDIR

  ;Now you can list files that should be extracted to this output path or create
  ;directories:

  File /r "dist\Uploader\*"

SectionEnd
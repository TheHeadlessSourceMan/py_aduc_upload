pyinstaller -y --icon=octopus.ico -w octopus_ui.py -n "Octopus"
pyinstaller -y --icon=serial.ico aduc_upload.py -n "Uploader"
makensis /P 4 py_aduc_upload_setup.nsi

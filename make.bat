pyinstaller --onedir --exclude-module py_aduc_upload --paths=. --icon=octopus.ico -w octopus_ui.py -n "Octopus" --distpath "dist"
pyinstaller --onedir --exclude-module py_aduc_upload --paths=. --icon=serial.ico aduc_upload.py -n "Uploader" --distpath "dist"
makensis /P 4 py_aduc_upload_setup.nsi

# py_aduc_upload

TODO: This is a work in progress and not currently functional!

Python interface to the serial uploader for Analog Devices ADuC70xx family of devices.

This includes the popular ADuC-7020 chip as found in development boards like the
Olimex ADUC-H7020 and Analog Devices EVAL-ADUC7020 as well as in many popular embedded devices.

Consider it a more useable form of the official ARMWSD-UART.exe program.

General useage:
```
  ac=AducConnection('COM1')
  if ac.upload('myprogram.hex'):
    ac.run()
```
Or use the shortcut function:
```
  upload('myprogram.hex','COM1',andRun=True)
```

Naturally, there is a command line as well.

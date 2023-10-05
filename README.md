# py_aduc_upload

Python interface to the serial uploader for Analog Devices (ADuC70xx)[https://www.analog.com/en/products/aduc7020.html] family of devices.

This includes the popular ADuC-7020 chip as found in development boards like the
(Olimex ADUC-H7020)[https://www.olimex.com/Products/ARM/AnalogDevices/ADuC-H7020/] and (Analog Devices EVAL-ADUC7020)[https://www.analog.com/en/design-center/evaluation-hardware-and-software/evaluation-boards-kits/EVAL-ADUC7020.html] as well as in many popular embedded devices.

Consider it a more useable, more universal, form of the official ARMWSD-UART.exe program.

## Status
   * generally working (verified on Olimex ADUC-H7020)
   * unit tests are a disaster

## Installation instructions
   1. requres python and the pyserial and intelhex libraries, so do something like
   ```pip install pyserial intelhex```
   2. run the python file from the command line or import it into your own python script (see below)

## General useage
From your python script:
```
  ac=AducConnection('COM1')
  if ac.upload('myprogram.hex'):
    ac.run()
```

Or use the shortcut function:
```
  upload('myprogram.hex','COM1',andRun=True)
```

Naturally, there is a command line as well:
```
  py_aduc_upload.py --port=COM1 myprogram.hex --run
```

And, yes, it has help info:
```
  py_aduc_upload.py --help
```

## Reference
For more info on the protocol, see:
    [https://www.analog.com/media/en/technical-documentation/application-notes/AN-724.pdf]
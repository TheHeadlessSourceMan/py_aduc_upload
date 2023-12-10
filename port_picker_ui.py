import typing
import os
from tkinter import *
from tkinter.ttk import *
import serial.tools.list_ports


class PortPickerWindow(Tk):
    """
    UI window for octopus.  Useage:
    PortPickerWindow().mainloop()

    Generally it's easier to use the askForPort() function instead
    """
    def __init__(self,
        ignorePorts:typing.Optional[typing.Iterable[str]]=None):
        """ """
        Tk.__init__(self)
        self.selectedPort:typing.Optional[str]=None
        self.title('')
        self.geometry('150x50')
        self.iconbitmap(os.sep.join((os.path.abspath(__file__).rsplit(os.sep,1)[0],"serial.ico")))
        self.comboboxValue=StringVar()
        self.ports=[]
        for port in serial.tools.list_ports.comports():
            if ignorePorts is not None and port not in ignorePorts:
                self.ports.append(port)
        label=Label(self,text='Select serial port')
        label.pack()
        combo=Combobox(self,textvariable=self.comboboxValue,values=self.ports)
        combo.pack()
        combo.bind('<<ComboboxSelected>>',self.onSelect)

    def onSelect(self,*args):
        self.selectedPort=self.comboboxValue.get()
        self.destroy()


def askForPort(dontAskIfOnlyOne:bool=True,
    ignorePorts:typing.Optional[typing.Iterable[str]]=None
    )->typing.Optional[str]:
    """
    pop up a dialog to allow the user to select a serial port

    if dontAskIfOnlyOne then if there is only one port, return it
    if there are no serial ports, returns None immediately
    """
    ppw=PortPickerWindow(ignorePorts)
    if not ppw.ports:
        return None
    if len(ppw.ports)==1 and dontAskIfOnlyOne:
        return ppw.ports[0]
    ppw.mainloop()
    return ppw.selectedPort


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    printhelp=False
    dontAskIfOnlyOne:bool=False
    ignorePorts:typing.List[str]=[]
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            av[0]=av[0].lower()
            if av[0] in ('-h','--help'):
                printhelp=True
            elif av[0]=='--dna1':
                dontAskIfOnlyOne=True
            elif av[0] in ('--ignore','--ignoreports'):
                ignorePorts.extend(av[1].replace(' ','').split(','))
            else:
                printhelp=True
        else:
            printhelp=True
    if not printhelp:
        port=askForPort(dontAskIfOnlyOne,ignorePorts=ignorePorts)
        print(port)
    if printhelp:
        print('USEAGE:')
        print('  port_picker_ui [options]')
        print('OPTIONS:')
        print('  -h ............................. this help')
        print('  --dna1 ......................... do not ask if there\'s only one')
        print('  --ignore=port[,port,...] ....... ignore checking on certain com ports')
        print('  --ignorePorts=port[,port,...] .. ignore checking on certain com ports')
        return 1
    return 0

if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))

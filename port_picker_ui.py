"""
UI window for octopus.  Useage:
PortPickerWindow().mainloop()

Generally it's easier to use the askForPort() function instead
because it can do things like not pop up the window when it's not necessary
"""
import typing
import os
import tkinter as tk
import tkinter.ttk as ttk
import serial.tools.list_ports # type: ignore


class PortPickerWindow(tk.Tk):
    """
    UI window for octopus.  Useage:
    PortPickerWindow().mainloop()

    Generally it's easier to use the askForPort() function instead
    because it can do things like not pop up the window when it's not necessary
    """

    # ports list shared between all instances
    _ports:typing.Optional[typing.List[str]]=None

    def __init__(self,
        ignorePorts:typing.Optional[typing.Iterable[str]]=None):
        """ """
        tk.Tk.__init__(self)
        self.selectedPort:typing.Optional[str]=None
        self.ignorePorts=ignorePorts
        self.title('')
        self.geometry('150x50')
        here=os.path.abspath(__file__).rsplit(os.sep,1)[0]
        self.iconbitmap(os.sep.join((here,"serial.ico")))
        self.comboboxValue=tk.StringVar()
        self._label=tk.StringVar(value='Select serial port')
        label=ttk.Label(self,textvariable=self._label)
        label.pack()
        values=[p for p in self.validPorts]
        self.combo=ttk.Combobox(self,
            textvariable=self.comboboxValue,values=values)
        self.combo.pack()
        self.combo.bind('<<ComboboxSelected>>',self.onSelect)
        self._refreshTimerKeepGoing=True
        self.after(1000,self.onTimer)

    @property
    def label(self)->str:
        """
        Get set the prompt label for the port picker
        """
        return self._label.get()
    @label.setter
    def label(self,label:str):
        return self._label.set(label)

    def onTimer(self):
        """
        Will re-check the ports every second
        """
        if self._refreshTimerKeepGoing:
            oldValues:typing.List[str]=self.getValidPorts(False)
            newValues:typing.List[str]=self.getValidPorts(True)
            # only want to update the combo if the port list changes
            # to minimize ui disruption (losing mouse focus, etc)
            updateCombobox=False
            if len(oldValues)!=len(newValues):
                updateCombobox=True
            else:
                try:
                    for v in oldValues:
                        _=newValues.index(v)
                except IndexError:
                    updateCombobox=True
            if updateCombobox:
                self.combo.configure(values=newValues)
            # check again in another second
            self.after(1000,self.onTimer)

    def __del__(self):
        self._refreshTimerKeepGoing=False

    def onSelect(self,*_):
        """
        called when a port is selected in the combo box
        """
        self._refreshTimerKeepGoing=False
        self.selectedPort=self.comboboxValue.get()
        self.destroy()

    @classmethod
    def refreshPorts(cls)->None:
        """
        refresh the global ports list

        NOTE: this is a class method, so the ports list can
        be inspected without creating a TK window
        """
        cls._ports=[]
        for port in serial.tools.list_ports.comports():
            port=str(port).strip().split(maxsplit=1)[0]
            cls._ports.append(port)

    @classmethod
    def getPorts(cls,
        ignorePorts:typing.Optional[typing.Iterable[str]]=None,
        forceRefresh:bool=False
        )->typing.Iterable[str]:
        """
        get a list of available ports

        :ignorePorts: allows you to skip over unwanted ports
        :forceRefresh: always refresh the ports list

        NOTE: this is a class method, so the ports list can
        be inspected without creating a TK window
        """
        if forceRefresh or cls._ports is None:
            cls.refreshPorts()
        if ignorePorts is None or not ignorePorts:
            return cls._ports
        ports=[]
        if cls._ports is not None:
            for port in cls._ports:
                if port not in ignorePorts:
                    ports.append(port)
        return ports

    @property
    def validPorts(self)->typing.Iterable[str]:
        """
        All valid ports

        NOTE: using getValidPorts() gives you the
        option of refreshing the port list
        """
        return self.getValidPorts()

    def getValidPorts(self,forceRefresh:bool=False)->typing.Iterable[str]:
        """
        Get a list of all valid ports

        :forceRefresh: always refresh the ports list
        """
        return self.getPorts(self.ignorePorts,forceRefresh)

def askForPort(dontAskIfOnlyOne:bool=True,
    ignorePorts:typing.Optional[typing.Iterable[str]]=None,
    forceRefresh:bool=False,
    askIfZero:bool=False,
    )->typing.Optional[str]:
    """
    optionally pop up a dialog to allow the user to select a serial port

    :dontAskIfOnlyOne: if there is only one port, return it
        if there are no serial ports, returns None immediately
    :askIfZero: if there are no ports, ask anyway
        use case is: user will plug something in and the list will update
    """
    ports=PortPickerWindow.getPorts(ignorePorts,forceRefresh)
    if not ports and not askIfZero:
        return None
    if len(ports)==1 and dontAskIfOnlyOne:
        return ports[0]
    ppw=PortPickerWindow(ignorePorts)
    ppw.mainloop()
    return ppw.selectedPort


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    printhelp=False
    dontAskIfOnlyOne:bool=False
    askIfZero:bool=False
    ignorePorts:typing.List[str]=[]
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            av[0]=av[0].lower()
            if av[0] in ('-h','--help'):
                printhelp=True
            elif av[0]=='--dna1':
                dontAskIfOnlyOne=True
            elif av[0]=='--ask0':
                askIfZero=True
            elif av[0] in ('--ignore','--ignoreports'):
                ignorePorts.extend(av[1].replace(' ','').split(','))
            else:
                printhelp=True
        else:
            printhelp=True
    if not printhelp:
        port=askForPort(dontAskIfOnlyOne,
            ignorePorts=ignorePorts,askIfZero=askIfZero)
        print(port)
    if printhelp:
        print('USEAGE:')
        print('  port_picker_ui [options]')
        print('OPTIONS:')
        print('  -h ............................. this help')
        print('  --ask0 ......................... ask if there are none')
        print('           (assumes they will plug in something')
        print('          causing the port list to update)')
        print('  --dna1 ......................... do not ask if only 1 exists')
        print('  --ignore=port[,port,...] ....... ignore certain com ports')
        print('  --ignorePorts=port[,port,...] .. ignore certain com ports')
        return 1
    return 0

if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))

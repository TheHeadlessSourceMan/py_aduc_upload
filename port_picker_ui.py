"""
UI window for octopus.

Usage:
PortPickerWindow().mainloop()

Generally it's easier to use the askForPort() function instead
because it can do things like not pop up the window when it's not necessary
"""
import typing
import time
import os
import tkinter as tk
import tkinter.ttk as ttk
from serial import Serial,SerialException # type: ignore
import serial.tools.list_ports # type: ignore
from py_aduc_upload import SerialLike,PortValidationFunction


FoundPort=typing.Tuple[
    str,typing.Optional[SerialLike],typing.Any]

class PortPickerWindow(tk.Toplevel):
    """
    UI window for octopus.

    Usage:
    PortPickerWindow().mainloop()

    Generally it's easier to use the askForPort() function instead
    because it can do things like not pop up the window when it's not necessary
    """

    # ports list shared between all instances
    _ports:typing.Optional[typing.List[str]]=None

    def __init__(self,
        ignorePorts:typing.Optional[typing.Iterable[str]]=None,
        caption:typing.Optional[str]=None,
        title:typing.Optional[str]=None,
        tkMaster:typing.Any=None,
        validationCallback:typing.Optional[PortValidationFunction]=None,
        validationCallbackParams:typing.Optional[
            typing.Dict[str,typing.Any]]=None):
        """ """
        tk.Toplevel.__init__(self,master=tkMaster)
        if caption is None:
            caption='Select serial port'
        if title is None:
            title='Select serial port'
        self.validationCallback=validationCallback
        self.validationCallbackParams=validationCallbackParams
        self.selectedPort:typing.Optional[str]=None
        self.ignorePorts=ignorePorts
        self.title(title)
        w=150#+7*len(title)
        h=55
        self.geometry(f'{w}x{h}')
        here=os.path.abspath(__file__).rsplit(os.sep,1)[0]
        self.iconbitmap(os.sep.join((here,"serial.ico")))
        self.comboboxValue=tk.StringVar()
        label=ttk.Label(self,text=caption)
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
        return self.label.get()
    @label.setter
    def label(self,label:str):
        return self.label.set(label)

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
                    for v in newValues:
                        _=oldValues.index(v)
                except IndexError:
                    updateCombobox=True
            if updateCombobox:
                self.combo.configure(values=newValues)
            # check again in another second
            try:
                self.after(1000,self.onTimer)
            except Exception as e:
                print(e)

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
        forceRefresh:bool=False,
        validationCallback:typing.Optional[PortValidationFunction]=None,
        validationCallbackParams:typing.Optional[
            typing.Dict[str,typing.Any]]=None
        )->typing.Iterable[FoundPort]:
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
                device=None
                info=None
                if port in ignorePorts:
                    continue
                if validationCallback is not None:
                    if validationCallbackParams is None:
                        validationCallbackParams={}
                    device=Serial(port)
                    info=validationCallback(device,**validationCallbackParams)
                    if info is None:
                        continue
                ports.append((port,device,info))
        return ports

    @property
    def validPorts(self)->typing.Iterable[FoundPort]:
        """
        All valid ports

        NOTE: using getValidPorts() gives you the
        option of refreshing the port list
        """
        return self.getValidPorts()

    def getValidPorts(self,
        forceRefresh:bool=False
        )->typing.Iterable[FoundPort]:
        """
        Get a list of all valid ports

        :forceRefresh: always refresh the ports list
        """
        return self.getPorts(self.ignorePorts,forceRefresh)


def askForPort(
    dontAskIfOnlyOne:bool=True,
    ignorePorts:typing.Optional[typing.Iterable[str]]=None,
    forceRefresh:bool=False,
    askIfZero:bool=False,
    baud:int=115200,
    tkMaster:typing.Any=None,
    portPickerCaption:typing.Optional[str]=None,
    validatePortFn:typing.Optional[
        PortValidationFunction
        ]=None,
    validatePortParams:typing.Optional[typing.Dict[str,typing.Any]]=None,
    )->typing.Optional[FoundPort]:
    """
    optionally pop up a dialog to allow the user to select a serial port

    :ignorePorts: list of ports to be ignored in the search
    :dontAskIfOnlyOne: if there is only one port, return it
        if there are no serial ports, returns None immediately
    :askIfZero: if there are no ports, ask anyway
        use case is: user will plug something in and the list will update
    :baud: required if doing searchVersionString
    :tkMaster: when popping up a new window, use this as the parent
    :portPickerCaption: caption to use for any port picker popup
    :validatePortFn: a validation function that discerns a port we are
        looking for vs other ports that are just "there"
    :validatePortParams: extra params to pass to validatePortFn(serial,...)

    :return: (port name, already open port, device info)
        where any could be None
    """
    portName=None
    openPort=None
    deviceInfo=None
    if validatePortParams is None:
        validatePortParams={}
    portsPlus:typing.Dict[str,
        typing.Tuple[SerialLike,typing.Any]]={}
    if not ignorePorts:
        ignorePorts=[]
    else:
        ignorePorts=list(ignorePorts)
    portNames:typing.List[str]=[p for p in
        PortPickerWindow.getPorts(ignorePorts,forceRefresh)]
    # do a second pass to validate each port
    if validatePortFn is not None:
        for portName in portNames:
            # open the device and ask for its name
            print(f'Attempting to query port {portName} (baud={baud})')
            try:
                openPort=Serial(portName,baud,
                    timeout=2.0,inter_byte_timeout=0.01)
            except SerialException:
                print('  busy.')
                continue
            while not openPort.is_open:
                time.sleep(0.1)
            info=validatePortFn(openPort,**validatePortParams)
            if info is not None:
                portsPlus[portName]=(openPort,info)
            else:
                ignorePorts.append(portName)
                openPort.close()
        portNames=list(portsPlus.keys())
    if not portNames and not askIfZero:
        return (None,None,None)
    if len(portNames)==1 and dontAskIfOnlyOne:
        portName=portNames[0]
    else:
        ppw=PortPickerWindow(
            ignorePorts,portPickerCaption,tkMaster=tkMaster)
        ppw.wait_window(ppw)
        portName=ppw.selectedPort
    if portsPlus and portName is not None:
        openPort,deviceInfo=portsPlus.get(portName,(None,None))
        if openPort is not None:
            del portsPlus[portName]
        for port,_ in portsPlus.values():
            port.close()
    if openPort is not None:
        openPort.reset_input_buffer()
        openPort.reset_output_buffer()
    return (portName,openPort,deviceInfo)


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    printHelp=False
    dontAskIfOnlyOne:bool=False
    askIfZero:bool=False
    ignorePorts:typing.List[str]=[]
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            av[0]=av[0].lower()
            if av[0] in ('-h','--help'):
                printHelp=True
            elif av[0]=='--dna1':
                dontAskIfOnlyOne=True
            elif av[0]=='--ask0':
                askIfZero=True
            elif av[0] in ('--ignore','--ignoreports'):
                ignorePorts.extend(av[1].replace(' ','').split(','))
            else:
                printHelp=True
        else:
            printHelp=True
    if not printHelp:
        port=askForPort(dontAskIfOnlyOne,
            ignorePorts=ignorePorts,askIfZero=askIfZero)
        if port[2]:
            print(f'{port[0]} = {port[2]}')
        else:
            print(port[0])
    if printHelp:
        print('USAGE:')
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

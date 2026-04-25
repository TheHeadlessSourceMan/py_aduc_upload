"""
UI window for octopus.

Usage:
PortPickerWindow().mainloop()

Generally it's easier to use the askForPort() function instead
because it can do things like not pop up the window when it's not necessary
"""
import typing
import os
import tkinter as tk
import tkinter.ttk as ttk
from serial import Serial # type: ignore
import serial.tools.list_ports # type: ignore
from py_aduc_upload import SerialLike,PortValidationFunction


FoundPort=typing.Tuple[
    str,typing.Optional[SerialLike],typing.Optional[typing.Any]]

_SerialPortEnumeratorFn=typing.Callable[[],typing.Iterable[FoundPort]]
SerialPortEnumerator=typing.Union[
    _SerialPortEnumeratorFn,
    typing.Tuple[_SerialPortEnumeratorFn,typing.Dict[str,typing.Any]]]

class PortPickerWindow(tk.Toplevel):
    """
    UI window for octopus.

    Usage:
    PortPickerWindow().mainloop()

    Generally it's easier to use the askForPort() function instead
    because it can do things like not pop up the window when it's not necessary
    """

    # ports list shared between all instances
    _ports:typing.Optional[typing.List[FoundPort]]=None

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
        self.enumerators=[self.systemComPortEnumerator]
        self.title(title)
        w=150#+7*len(title)
        h=55
        self.geometry(f'{w}x{h}')
        here=os.path.abspath(__file__).rsplit(os.sep,1)[0]
        self._iconHandle=tk.PhotoImage(file=os.sep.join((here,"serial.png")))
        self.iconphoto(False,self._iconHandle)
        #self.iconbitmap(os.sep.join((here,"serial.ico")))
        self.comboboxValue=tk.StringVar()
        self._label=tk.StringVar(value=caption)
        label=ttk.Label(self,textvariable=self._label)
        label.pack()
        values=[p[0] for p in self.validPorts]
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

    def onTimer(self)->None:
        """
        Will re-check the ports every second
        """
        if self._refreshTimerKeepGoing:
            oldValues:typing.List[FoundPort]=list(self.getValidPorts(False))
            newValues:typing.List[FoundPort]=list(self.getValidPorts(True))
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
                except ValueError:
                    updateCombobox=True
            if updateCombobox:
                self.combo.configure(values=[port[0] for port in newValues])
            # check again in another second
            try:
                self.after(1000,self.onTimer)
            except Exception as e:
                print(e)

    def __del__(self):
        self._refreshTimerKeepGoing=False

    def onSelect(self,*_:typing.ParamSpecArgs)->None:
        """
        called when a port is selected in the combo box
        """
        self._refreshTimerKeepGoing=False
        self.selectedPort=self.comboboxValue.get()
        self.destroy()

    @classmethod
    def systemComPortEnumerator(cls)->typing.Iterable[FoundPort]:
        """
        Enumerate the names of system com ports
        """
        return [(str(port).strip().split(maxsplit=1)[0],None,None)
            for port in serial.tools.list_ports.comports()]

    @classmethod
    def refreshPorts(cls,
        enumerators:typing.Optional[typing.Iterable[SerialPortEnumerator]]=None
        )->None:
        """
        refresh the global ports list

        NOTE: this is a class method, so the ports list can
        be inspected without creating a TK window
        """
        if enumerators is None:
            enumerators=[PortPickerWindow.systemComPortEnumerator]
        cls._ports=[]
        portNames:typing.Set[str]=set()
        for enumerator in enumerators:
            enumeratorParams={}
            if isinstance(enumerator,tuple):
                enumeratorParams=enumerator[1] # noqa: E501 # pylint: disable=line-too-long,unsubscriptable-object # I don't know why it thinks this is unsubscriptable when I do a specific type check to ensure it is a tuple
                enumerator=enumerator[0] # noqa: E501 # pylint: disable=line-too-long,unsubscriptable-object
            for port in enumerator(**enumeratorParams):
                portName=port[0]
                if port[1] is not None:
                    portName=port[1].name
                    if hasattr(port[1],"port"):
                        portName=port[1].port
                if portName not in portNames:
                    portNames.add(portName)
                    cls._ports.append(port)

    @classmethod
    def getPorts(cls,
        ignorePorts:typing.Optional[typing.Iterable[str]]=None,
        forceRefresh:bool=False,
        validationCallback:typing.Optional[PortValidationFunction]=None,
        validationCallbackParams:typing.Optional[
            typing.Dict[str,typing.Any]]=None,
        enumerators:typing.Optional[
            typing.Iterable[SerialPortEnumerator]]=None,
        baudRate:int=115200
        )->typing.Iterable[FoundPort]:
        """
        get a list of available ports

        :ignorePorts: allows you to skip over unwanted ports
        :forceRefresh: always refresh the ports list

        NOTE: this is a class method, so the ports list can
        be inspected without creating a TK window
        """
        if enumerators is None:
            enumerators=(cls.systemComPortEnumerator,)
        if forceRefresh or cls._ports is None:
            cls.refreshPorts(enumerators)
        if ignorePorts is None:
            ignorePorts=[]
        ports:typing.List[FoundPort]=[]
        if cls._ports is not None:
            for port in cls._ports:
                info=None
                if port[0] in ignorePorts:
                    continue
                if validationCallback is not None:
                    if validationCallbackParams is None:
                        validationCallbackParams={}
                    if port[1] is None:
                        try:
                            port=(
                                port[0],
                                Serial(port[0],baudrate=baudRate),
                                port[2])
                        except Exception as e:
                            if str(e).find('Access is denied.')>=0:
                                print(f'Port {port[0]} in use. Skipping.')
                            else:
                                print(f'Exception while accessing port {port[0]}')
                                print(e)
                            continue
                    info=validationCallback(
                        port[1],**validationCallbackParams) # type: ignore
                    if info is None:
                        continue
                    if port[2] is None:
                        port=(
                            port[0],
                            port[1],
                            info)
                ports.append(port)
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
        return self.getPorts(
            self.ignorePorts,forceRefresh,enumerators=self.enumerators)


def askForPort(
    dontAskIfOnlyOne:bool=True,
    ignorePorts:typing.Optional[typing.Iterable[str]]=None,
    forceRefresh:bool=False,
    askIfZero:bool=False,
    baudRate:int=115200,
    tkMaster:typing.Any=None,
    portPickerCaption:typing.Optional[str]=None,
    validatePortFn:typing.Optional[
        PortValidationFunction
        ]=None,
    validatePortParams:typing.Optional[typing.Dict[str,typing.Any]]=None,
    enumerators:typing.Optional[typing.Iterable[SerialPortEnumerator]]=None
    )->typing.Tuple[str,typing.Optional[SerialLike],typing.Any]:
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
    :enumerators: functions that can enumerate serial ports

    :return: (port name, already open port, device info)
        where any could be None
    """
    if enumerators is None:
        enumerators=(PortPickerWindow.systemComPortEnumerator,)
    portName=None
    selectedPort:FoundPort=\
        ('',None,None)
    if validatePortParams is None:
        validatePortParams={}
    if not ignorePorts:
        ignorePorts=[]
    else:
        ignorePorts=list(ignorePorts)
    ports=list(PortPickerWindow.getPorts(
        ignorePorts,forceRefresh,
        validationCallback=validatePortFn,
        validationCallbackParams=validatePortParams,
        enumerators=enumerators,
        baudRate=baudRate))
    if not ports and not askIfZero:
        return selectedPort
    if len(ports)==1 and dontAskIfOnlyOne:
        selectedPort=ports[0]
    else:
        ppw=PortPickerWindow(
            ignorePorts,portPickerCaption,tkMaster=tkMaster)
        ppw.wait_window(ppw)
        portName=ppw.selectedPort
        if portName is None:
            return selectedPort
        # find which port they selected
        selectedPort=(portName,None,None)
        for port in ports:
            if port[1] is not None:
                if hasattr(port[1],"port") \
                    and port[1].port==portName: # type: ignore
                    if selectedPort[1] is None:
                        selectedPort=port
                    continue
                elif port[1].name==portName:
                    if selectedPort[1] is None:
                        selectedPort=port
                    continue
                # not the one we're after, so be clean and close it
                port[1].close()
    # clear the io for good measure
    if selectedPort[1] is not None and selectedPort[1].is_open:
        selectedPort[1].reset_input_buffer()
        selectedPort[1].reset_output_buffer()
    return selectedPort


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

"""
A flash loader ui capable of flashing a nuber of
devices to the same image all at the same time!
"""
import typing
import os
import threading
import queue
import time
from tkinter import *
from tkinter.ttk import *
from aduc_upload import AducConnection,AducStatus
import intelhex
try:
    import serial
    import serial.tools.list_ports
except ImportError as e:
    print('pyserial not found.  Try something like:')
    print('    pip install pyserial')
    raise e

class PortStatusMessage:
    """
    A message envelope to be passed from port events
    to the ui for display.
    """
    def __init__(self,
        portName:typing.Optional[str]=None,
        progress:typing.Optional[float]=None,
        status:typing.Optional[str]=None,
        assignPortsList:typing.Optional[typing.Iterable[str]]=None):
        """ """
        self.portName=portName
        self.progress=progress
        self.status=status
        self.assignPortsList=assignPortsList


class PortStatusComponent(LabelFrame):
    """
    UI component to maintain status info about a serial port
    """

    def __init__(self,portComponents:"PortComponents",root:Frame,portName:str):
        self.name=portName
        LabelFrame.__init__(self,root,text=portName,padding=5)
        self.statusVar=StringVar(root,'Initializing...')
        self.statusControl=Label(self,textvariable=self.statusVar)
        self.statusControl.pack(expand=True, fill='x')
        self.progressControl=Progressbar(self,length=100)
        self.progressControl.pack(expand='yes', fill='x')
        #self.pack(expand='yes', fill='x')
        self._progress=0.0
        self._status=''
        self.portComponents=portComponents
        self._threadExit=False
        self._thread:typing.Optional[threading.Thread]=None
        self.start()

    @property
    def ihex(self)->intelhex.IntelHex:
        return self.portComponents.ihex

    @property
    def postRun(self)->str:
        return self.portComponents.postRun

    def start(self):
        """
        Start the thread (called automatically on creation)
        """
        if self._thread is None:
            self._threadExit=False
            self._thread=threading.Thread(target=self.run)
            self._thread.start()

    def _statusCB(self,status:AducStatus)->None:
        """
        callback from the uploader itself
        """
        self.status=str(status)
    def _percentCB(self,percent:float)->None:
        """
        callback from the uploader itself
        """
        self.progress=percent

    def run(self):
        """
        main loop of the thread
        """
        connection=AducConnection(port=self.name,statusCB=self._statusCB,percentCB=self._percentCB)
        while not self._threadExit:
            try:
                connection.uploadIhex(self.ihex,andVerify=True,andReset=True,postRun=self.postRun)
            except Exception as e:
                print(e)
                status=str(e).replace('\n',' ').replace('  ',' ')
                if len(status)>50:
                    status=status[0:47]+'...'
                self.status=status
                for i in range(10):
                    # wait for the user to be able to see that there was a problem
                    # use the progress bar as a count-down
                    self.progress=1.0-i/10
                    time.sleep(1)
                #raise e

    def stop(self):
        """
        stop the thread
        """
        if self._thread is not None:
            self._threadExit=True
            self._thread.join()
            self._thread=None

    def _setUiStatus(self,value:str):
        """
        runs in the ui thread to actually update the component
        """
        self.statusVar.set(str(value))

    def getStatus(self)->str:
        """
        Get the status message
        """
        return self._progress
    @property
    def status(self)->str:
        """
        Get the status message
        """
        return self.getStatus()

    def setStatus(self,status:str):
        """
        Set the status message
        """
        if self._status!=status:
            self._status=status
            msg=PortStatusMessage(self.name,status=str(status))
            self.portComponents._messageQueue.put(msg)
    @status.setter
    def status(self,status:str):
        """
        Set the status message
        """
        self.setStatus(status)

    def _setUiProgress(self,progress:float):
        """
        runs in the ui thread to actually update the component
        """
        self.progressControl['value']=progress*100

    def getProgress(self)->float:
        """
        Get the progress bar progress
        """
        return self._progress
    @property
    def progress(self)->float:
        """
        Get the progress bar progress
        """
        return self.getProgress()

    def setProgress(self,progress:float):
        """
        Set the progress bar progress
        """
        progress=min(progress,1.0)
        if self._progress!=progress:
            self._progress=progress
            msg=PortStatusMessage(self.name,progress=progress)
            self.portComponents._messageQueue.put(msg)
    @progress.setter
    def progress(self,progress:float):
        """
        Set the progress bar progress
        """
        self.setProgress(progress)


class PortComponents:
    """
    Maintain a list of PortStatusComponent controls
    """

    def __init__(self,root,
        filename:typing.Optional[str]=None,
        postRun:str="",
        portNames:typing.Union[None,str,typing.Iterable[str]]=None,
        ignorePorts:typing.Optional[typing.Iterable[str]]=None):
        """ """
        self.postRun=postRun
        self.filename=filename
        self.root=root
        if ignorePorts is None:
            ignorePorts=[]
        self.ignorePorts=list(ignorePorts)
        self._ihex:typing.Optional[intelhex.IntelHex]=None
        self._lastFileReadTimestamp:typing.Optional[typing.Any]=None
        self._lastFileReadSize:typing.Optional[typing.Any]=None
        self._components:typing.Dict[str,PortStatusComponent]={}
        self._messageQueue:queue.Queue[PortStatusMessage]=queue.Queue[PortStatusMessage]()
        self.extend(portNames)
        self._threadExit=False
        self._thread:typing.Optional[threading.Thread]=None
        self.start()

    @property
    def ihex(self)->intelhex.IntelHex:
        """
        hex data

        Will keep an eye on the file filename and re-update what this returns
        if the file changes!

        WARNING: if relying on auto-converting a .elf, this may not downgrade
            versions properly.  Use .hex files if you want to downgrade versions!
        """
        timestamp=os.path.getmtime(self.filename)
        size=os.path.getsize(self.filename)
        if self._ihex is None or self._lastFileReadTimestamp!=timestamp or size!=self._lastFileReadSize:
            tmpConn=AducConnection()
            self._ihex=tmpConn.loadIhex(self.filename)
            self._lastFileReadSize=size
            self._lastFileReadTimestamp=timestamp
        return self._ihex

    def start(self):
        """
        Start the thread (called automatically on creation)
        """
        if self._thread is None:
            self._threadExit=False
            self.thread=threading.Thread(target=self.run)
            self.thread.start()

    def run(self):
        """
        main loop of the thread
        """
        while not self._threadExit:
            newlist=[x.name for x in serial.tools.list_ports.comports()]
            msg=PortStatusMessage(assignPortsList=newlist)
            self._messageQueue.put(msg)
            time.sleep(30)

    def stop(self):
        """
        stop the thread
        """
        if self._thread is not None:
            self._threadExit=True
            self._thread.join()
            self._thread=None

    def __getitem__(self,portName:str):
        return self.add(portName)
    def __delitem__(self,portName:str):
        return self.remove(portName)

    def add(self,portName:str)->typing.Optional[PortStatusComponent]:
        """
        Add a single port
        """
        if portName in self.ignorePorts:
            return None
        if portName in self._components:
            return self._components[portName]
        created=PortStatusComponent(self,self.root,portName)
        self._components[portName]=created
        return created
    append=add

    def extend(self,
        portNames:typing.Union[None,str,typing.Iterable[str]]=None
        )->typing.Iterable[PortStatusComponent]:
        """
        Add a series of ports
        """
        ret=[]
        if portNames is None:
            return ret
        if isinstance(portNames,str):
            portNames=(portNames,)
        for pn in portNames:
            ret.append(self.add(pn))
        return ret

    def assign(self,
        portNames:typing.Union[None,str,typing.Iterable[str]]=None
        )->typing.Iterable[PortStatusComponent]:
        """
        Assign this to exactly equal a series of ports
        """
        ret=[]
        if portNames is None:
            portNames=[]
        elif isinstance(portNames,str):
            portNames=(portNames,)
        stuffToRemove=[]
        for k in self._components.keys():
            if k not in portNames:
                stuffToRemove.append(k)
        for k in stuffToRemove:
            self.remove(k)
        for pn in portNames:
            ret.append(self.add(pn))
        return ret

    def remove(self,portName:str)->None:
        """
        Remove a single port
        """
        c=self._components.get(portName)
        if c is not None:
            c.destroy()
            c.stop()
            del self._components[portName]


class OctopusWindow(Tk,PortComponents):
    """
    UI window for octopus.  Useage:
    OctopusWindow().mainloop()
    """
    def __init__(self,
        filename:typing.Optional[str]=None,
        postRun:str="",
        ignorePorts:typing.Optional[typing.Iterable[str]]=None):
        """ """
        PortComponents.__init__(self,self,filename=filename,postRun=postRun,ignorePorts=ignorePorts)
        Tk.__init__(self)
        self.title('octopus')
        self.geometry('250x800')
        self.iconbitmap(os.sep.join((os.path.abspath(__file__).rsplit(os.sep,1)[0],"octopus.ico")))
        self._pollQueue()

    def _pollQueue(self):
        """
        grab things from the message queue and update the ui as necessary
        """
        try:
            while True:
                msg:PortStatusMessage=self._messageQueue.get_nowait()
                if msg.assignPortsList is not None:
                    self.assign(msg.assignPortsList)
                elif msg.portName in self._components:
                    if msg.progress is not None:
                        self._components[msg.portName]._setUiProgress(msg.progress)
                    if msg.status is not None:
                        self._components[msg.portName]._setUiStatus(msg.status)
        except queue.Empty:
            pass # it took us out of the loop, so it did its job
        # run again in a quarter second
        self.after(250,self._pollQueue)


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    printhelp=False
    postRun=''
    ignorePorts:typing.List[str]=[]
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            av[0]=av[0].lower()
            if av[0] in ('-h','--help'):
                printhelp=True
            elif av[0]=='--postrun':
                postRun=av[1]
            if av[0] in ('--ignore','--ignoreports'):
                ignorePorts.extend(av[1].replace(' ','').split(','))
            else:
                printhelp=True
        else:
            filename=arg
    if not printhelp:
        octopus=OctopusWindow(filename=filename,postRun=postRun,ignorePorts=ignorePorts)
        octopus.mainloop() # never returns
    if printhelp:
        print('USEAGE:')
        print('  octopus_ui [options] [filename]')
        print('OPTIONS:')
        print('  -h ............................. this help')
        print('  --postRun="shell command"  ..... run a shell command after the upload')
        print('  --ignore=port[,port,...] ....... ignore checking on certain com ports')
        print('  --ignorePorts=port[,port,...] .. ignore checking on certain com ports')
        return 1
    return 0

if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))
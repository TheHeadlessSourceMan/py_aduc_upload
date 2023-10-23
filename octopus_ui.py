import typing
import os
import threading
import queue
import time
import random
from tkinter import *
from tkinter.ttk import *


class PortStatusMessage:
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
        self.statusControl.pack(expand='yes', fill='x')
        self.progressControl=Progressbar(self,length=100)
        self.progressControl.pack(expand='yes', fill='x')
        self.pack(expand='no', fill='both')
        self._progress=0.0
        self._status=''
        self.portComponents=portComponents
        self._threadExit=False
        self._thread:typing.Optional[threading.Thread]=None
        self.start()

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
            time.sleep(0.1)
            self.progress=(self.progress+random.random()/10.0)%1.0

    def stop(self):
        """
        stop the thread
        """
        if self.thread is not None:
            self._threadExit=True
            self.thread.join()
            self.thread=None

    def _setUiStatus(self,value:str):
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
        status=str(status)
        if self._status!=status:
            self._status=status
            msg=PortStatusMessage(self.name,status=status)
            self.portComponents._messageQueue.put(msg)
    @status.setter
    def status(self,status:str):
        """
        Set the status message
        """
        self.setStatus(status)

    def _setUiProgress(self,progress:float):
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
    Maintaine a list of PortStatusComponent controls
    """

    def __init__(self,root,
        portNames:typing.Union[None,str,typing.Iterable[str]]=None,
        ignorePorts:typing.Optional[typing.Iterable[str]]=None):
        """ """
        self.root=root
        if ignorePorts is None:
            ignorePorts=[]
        self.ignorePorts=list(ignorePorts)
        self._components:typing.Dict[str,PortStatusComponent]={}
        self._messageQueue:queue.Queue[PortStatusMessage]=queue.Queue[PortStatusMessage]()
        self.extend(portNames)
        self._threadExit=False
        self._thread:typing.Optional[threading.Thread]=None
        self.start()

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
            time.sleep(5)
            newlist=list(self._components.keys())
            if random.random()>0.5:
                # add a port
                if len(newlist)<20:
                    r=random.randint(1,10)
                    for n in range(r,100):
                        s=f'COM{n}'
                        if s not in newlist:
                            newlist.append(s)
                            break
            else:
                # remove a port
                if len(newlist)>1:
                    newlist.pop(random.randint(0,len(newlist)))
            msg=PortStatusMessage(assignPortsList=newlist)
            self._messageQueue.put(msg)

    def stop(self):
        """
        stop the thread
        """
        if self.thread is not None:
            self._threadExit=True
            self.thread.join()
            self.thread=None

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
            return
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
    def __init__(self):
        PortComponents.__init__(self,self)
        Tk.__init__(self)
        self.title('octopus')
        self.geometry('250x800')
        self.iconbitmap(os.sep.join((os.path.abspath(__file__).rsplit(os.sep,1)[0],"oct.ico")))
        self._pollQueue()

    def _pollQueue(self):
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
        except Exception as e:
            if not isinstance(e,queue.Empty):
                raise e
        # run again in a quarter second
        self.after(250,self._pollQueue)


octopus=OctopusWindow()
octopus.append("COM1")
octopus.assign(("COM2","COM3"))
octopus.extend(("COM4"))
octopus.mainloop()
"""
Info and utils about windows devices
"""
import typing
import time
import subprocess
from winDevices.powershellColonObjects import (
    PowershellColonObject,PowershellColonObjects)

class WinDevice(PowershellColonObject):
    """
    Info and utils for a single windows device
    """
    def __init__(self,
        rawFromPowershell:typing.Optional[str]=None):
        """ """
        self.FriendlyName:str=""
        self.InstanceId:str=""
        self.Problem:str=""
        self.ConfigManagerErrorCode:str=""
        self.ProblemDescription:str=""
        self.Caption:str=""
        self.Description:str=""
        self.InstallDate:str=""
        self.Name:str=""
        self.Status:str=""
        self.Availability:str=""
        self.ConfigManagerUserConfig:str=""
        self.CreationClassName:str=""
        self.DeviceID:str=""
        self.ErrorCleared:str=""
        self.ErrorDescription:str=""
        self.LastErrorCode:str=""
        self.PNPDeviceID:str=""
        self.PowerManagementCapabilities:str=""
        self.PowerManagementSupported:str=""
        self.StatusInfo:str=""
        self.SystemCreationClassName:str=""
        self.SystemName:str=""
        self.ClassGuid:str=""
        self.CompatibleID:str=""
        self.HardwareID:str=""
        self.Manufacturer:str=""
        self.PNPClass:str=""
        self.Present:str=""
        self.Service:str=""
        self.PSComputerName:str=""
        self.CimClass:str=""
        self.CimInstanceProperties:str=""
        PowershellColonObject.__init__(self,rawFromPowershell)

    @property
    def properties(self)->PowershellColonObjects:
        """
        Properties about the device
        """
        return self.getProperties()

    def getProperties(self)->PowershellColonObjects:
        """
        Properties about the device
        """
        psCommand=f"Get-PnpDeviceProperty -InstanceID '{self.InstanceId}' | Select-Object *" # noqa: E501 # pylint: disable=line-too-long
        return PowershellColonObjects(psCommand=psCommand)

    def reset(self,offTimeSec=1.0):
        """
        Reset a device by power-cycling it
        """
        self.disable()
        time.sleep(offTimeSec)
        self.enable()
    powerCycle=reset

    def enable(self):
        """
        Enable a device

        See also:
        https://learn.microsoft.com/en-us/powershell/module/pnpdevice/enable-pnpdevice?view=windowsserver2022-ps
        """
        psCmd=f"Enable-PnpDevice -Confirm:$false -InstanceID '{self.InstanceId}'"
        cmd=['powershell','-Command',psCmd]
        po=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=po.communicate()
        errStr=err.decode('utf-8',errors='ignore').strip()
        if errStr:
            raise Exception(errStr)
        outStr=out.decode('utf-8',errors='ignore').strip().replace('\r','')
        print(outStr)
    on=enable

    def disable(self):
        """
        Disable a device

        NOTE: you must be an administrator to do this, for obvious reasons

        See also:
        https://learn.microsoft.com/en-us/powershell/module/pnpdevice/disable-pnpdevice?view=windowsserver2022-ps
        """
        psCmd=f"Disable-PnpDevice -Confirm:$false -InstanceID '{self.InstanceId}'"
        cmd=['powershell','-Command',psCmd]
        #print('\n'.join(cmd))
        po=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=po.communicate()
        errStr=err.decode('utf-8',errors='ignore').strip()
        if errStr:
            raise Exception(errStr)
        outStr=out.decode('utf-8',errors='ignore').strip().replace('\r','')
        print(outStr)
    off=disable

    def __str__(self):
        return f'"{self.FriendlyName}" ({self.PNPClass}) @ {self.InstanceId}'


class WinDevices(PowershellColonObjects):
    """
    Info and utils about windows devices

    Example:
    # Find and power-cycle COM4
    for device in WinDevices('Ports'):
        if device.Name.find('COM4')>=0:
            device.reset()
    """
    def __init__(self,
        loadDeviceClass:typing.Union[None,str,typing.Iterable[str]]=None):
        """
        :param loadDeviceClass: device class/classes to auto-load at startup
            you can always load more with getByDeviceClass()
        """
        self._byDeviceClass:typing.Dict[str,typing.List[WinDevice]]={}
        self._scannedAll:bool=False
        self.loadedClasses:typing.Set[str]=set()
        PowershellColonObjects.__init__(self)
        if loadDeviceClass:
            self.getByDeviceClass(loadDeviceClass)

    @property
    def jsonObj(self)->typing.List[typing.Dict[str,typing.Any]]:
        """
        This object as a json-compatable object
        """
        ret:typing.List[typing.Dict[str,typing.Any]]=[]
        for device in self.loaded:
            ret.append(device.jsonObj)
        return ret

    def __iter__(self)->typing.Iterator[WinDevice]:
        """
        Iterate over all loaded devices
        """
        return iter(self.getLoaded())

    def getLoaded(self,refresh:bool=False)->typing.Iterable[WinDevice]:
        """
        No, this isn't a wild frat party.
        This function gets all currently loaded/scanned devices.
        """
        if refresh:
            self.refresh()
        for vals in self._byDeviceClass.values():
            for val in vals:
                yield val

    @property
    def loaded(self)->typing.Iterable[WinDevice]:
        """
        All of the currently loaded/scanned devices
        """
        return self.getLoaded()

    def getAll(self,refresh:bool=False)->typing.Iterable[WinDevice]:
        """
        All of the devices on the computer
        """
        if refresh or not self._scannedAll:
            self.refresh()
        return self.getLoaded()

    @property
    def all(self)->typing.Iterable[WinDevice]:
        """
        All of the devices on the computer
        """
        return self.getAll()

    def getByDeviceClass(self,
        deviceClass:str,
        refresh:bool=False
        )->typing.Iterable[WinDevice]:
        """
        Get all devices of a certain device class (eg, "Ports")
        """
        if refresh or not self._byDeviceClass:
            self.refresh(deviceClass)
        elif not self._scannedAll:
            items=self._byDeviceClass.get(deviceClass)
            if items is not None:
                return items
            self.refresh(deviceClass)
        items=self._byDeviceClass.get(deviceClass,[])
        return items

    def refreshLoaded(self):
        """
        Refresh only the loaded deviceClass(es)
        """
        if self._scannedAll:
            self.refresh()
        else:
            self.refresh(self.loadedClasses)

    def refresh(self,
        deviceClass:typing.Union[None,str,typing.Iterable[str]]=None):
        """
        Refresh hardware list
        :deviceClass: specific device class or classes to refresh
            if None, then refresh all hardware on the system
        """
        if deviceClass is None:
            self._scannedAll=True
            psCmd='Get-PnPDevice | Select-Object *'
        elif not isinstance(deviceClass,str):
            for dc in deviceClass:
                self.refresh(dc)
            return
        else:
            self.loadedClasses.add(deviceClass)
            psCmd=f'Get-PnPDevice -Class {deviceClass} | Select-Object *'
        cmd=['powershell','-Command',psCmd]
        po=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=po.communicate()
        errStr=err.decode('utf-8',errors='ignore').strip()
        if errStr:
            raise Exception(errStr)
        outStr=out.decode('utf-8',errors='ignore').strip().replace('\r','')
        for result in outStr.split('\n\n'):
            dev=WinDevice(result)
            lst=self._byDeviceClass.get(dev.PNPClass)
            if lst is None:
                self._byDeviceClass[dev.PNPClass]=[dev]
            else:
                lst.append(dev)

    def __repr__(self):
        return '\n-----------------------\n'.join(
            [repr(item) for item in self.getLoaded()])

    def __str__(self):
        return '\n'.join(
            [str(item) for item in self.getLoaded()])


def getDevice(comOrInstanceId:str)->typing.Optional[WinDevice]:
    """
    get a device either by instance id or by com port name
    """
    if comOrInstanceId.upper().startswith('COM'):
        comOrInstanceId=comOrInstanceId.upper()
        wd=WinDevices("Ports")
        for dev in wd:
            if dev.Name.find(comOrInstanceId)>=0:
                return dev
        return None
    psCmd=f'Get-PnPDevice -InstanceId {comOrInstanceId} | Select-Object *'
    cmd=['powershell','-Command',psCmd]
    po=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err=po.communicate()
    errStr=err.decode('utf-8',errors='ignore').strip()
    if errStr:
        raise Exception(errStr)
    outStr=out.decode('utf-8',errors='ignore').strip().replace('\r','')
    for result in outStr.split('\n\n'):
        dev=WinDevice(result)
        return dev


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    printhelp=False
    if not args:
        printhelp=True
    else:
        outFormat='short'
        for arg in args:
            if arg.startswith('-'):
                arg=[a.strip() for a in arg.split('=',1)]
                if arg[0] in ['-h','--help']:
                    printhelp=True
                elif arg[0]=='--out':
                    outFormat=arg[1]
                elif arg[0]=='--ls':
                    wd=WinDevices()
                    if len(arg)>1:
                        wd.refresh(
                            [a.strip() for a in arg[1].split(',')])
                    else:
                        wd.refresh()
                    if outFormat=='json':
                        print(wd.json)
                    else:
                        print(wd)
                elif arg[0] in ('--dev','--device'):
                    dev=getDevice(arg[1])
                    if outFormat=='json':
                        print(dev.json)
                    else:
                        print(dev)
                elif arg[0] in ('--start','--on'):
                    dev=getDevice(arg[1])
                    dev.on()
                elif arg[0] in ('--stop','--off'):
                    dev=getDevice(arg[1])
                    dev.off()
                elif arg[0] in ('--reset','--restart'):
                    dev=getDevice(arg[1])
                    dev.reset()
                elif arg[0] in ('--properties','--props'):
                    dev=getDevice(arg[1])
                    print(dev.properties.json)
                else:
                    print('ERR: unknown argument "'+arg[0]+'"')
            else:
                print('ERR: unknown argument "'+arg+'"')
    if printhelp:
        print('Usage:')
        print('  winDevices.py [cmd] [options]')
        print('Options:')
        print('   -h ................... print this help')
        print('   --out=[short|jspn] ... ouput format')
        print('   --ls[=deviceClass] ... list all devices')
        print('      optionally, only devices of a certain class')
        print('      eg --ls=Ports')
        print('   --dev=[comX|instanceId] ..... find a single device')
        print('   --device=[comX|instanceId] .. find a single device')
        print('   --start=[comX|instanceId] ... turn a device on')
        print('   --on=[comX|instanceId] ...... turn a device on')
        print('   --stop=[comX|instanceId] .... turn a device off')
        print('   --off=[comX|instanceId] ..... turn a device off')
        print('   --restart=[comX|instanceId] . restart a device')
        print('   --properties=[comX|instanceId] ..... show device properties')


if __name__=='__main__':
    import sys
    cmdline(sys.argv[1:])

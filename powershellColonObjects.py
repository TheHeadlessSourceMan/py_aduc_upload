"""
Powershell objects characterized by key:value pairs
separated by colons
"""
import typing
import json


class PowershellColonObject:
    """
    Powershell object characterized by key:value pairs
    separated by colons
    """
    def __init__(self,
        rawFromPowershell:typing.Optional[str]=None):
        """ """
        if rawFromPowershell is not None:
            self.decodePsResult(rawFromPowershell)

    def decodePsResult(self,
        rawFromPowershell:typing.Optional[str]=None):
        """
        Decode from a raw powershell result
        """
        key=""
        val=""
        for line in rawFromPowershell.strip().split('\n'):
            if not line:
                continue
            elif line.startswith(' '): # continuation
                val=val+line.lstrip()
            else:
                kv=line.split(':',1)
                key=kv[0].rstrip()
                val=kv[1].lstrip()
            setattr(self,key,val)

    @property
    def json(self)->str:
        """
        This object as a json string
        """
        return self.jsonStr
    @property
    def jsonStr(self)->str:
        """
        This object as a json string
        """
        return json.dumps(self.jsonObj,indent=4)
    @property
    def jsonObj(self)->typing.Dict[str,typing.Any]:
        """
        This object as a json-compatable object
        """
        ret:typing.Dict[str,typing.Any]={}
        for k,v in self.__dict__.items():
            if k[0].isalpha() and k[0].isupper():
                ret[k]=v
        return ret

    def __repr__(self):
        return self.json


class PowershellColonObjects:
    """
    Powershell objects characterized by key:value pairs
    separated by colons
    """
    def __init__(self,
        rawFromPowershell:typing.Optional[str]=None,
        psCommand:typing.Optional[str]=None):
        """ """
        self._psObjects:typing.List[PowershellColonObject]=[]
        if rawFromPowershell is not None:
            self.decodePsResult(rawFromPowershell)
        if psCommand is not None:
            self.executeAndDecodeResult(psCommand)

    def executeAndDecodeResult(self,psCommand:str)->None:
        """
        Execute the given powershell command and then
        run decodePsResult() on what comes back
        """
        import subprocess
        cmd=['powershell','-Command',psCommand]
        po=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=po.communicate()
        errStr=err.decode('utf-8',errors='ignore').strip()
        if errStr:
            raise Exception(errStr)
        outStr=out.decode('utf-8',errors='ignore').strip().replace('\r','')
        self.decodePsResult(outStr)

    def decodePsResult(self,
        rawFromPowershell:str):
        """
        Decode from a raw powershell result
        """
        self._psObjects=[]
        rawFromPowershell.replace('\r','')
        for result in rawFromPowershell.split('\n\n'):
            dev=PowershellColonObject(result)
            self._psObjects.append(dev)

    def __iter__(self)->typing.Iterator[PowershellColonObject]:
        """
        Iterate over all loaded devices
        """
        return iter(self._psObjects)

    @property
    def json(self)->str:
        """
        This object as a json string
        """
        return self.jsonStr
    @property
    def jsonStr(self)->str:
        """
        This object as a json string
        """
        return json.dumps(self.jsonObj,indent=4)
    @property
    def jsonObj(self)->typing.List[typing.Dict[str,typing.Any]]:
        """
        This object as a json-compatable object
        """
        return [device.jsonObj for device in self]

    def __repr__(self):
        return '\n-----------------------\n'.join(
            [repr(item) for item in self])

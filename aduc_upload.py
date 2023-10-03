"""
Python interface to the serial uploader for Analog Devices ADuC70xx family of devices.

This includes the popular ADuC-7020 chip as found in development boards like the
Olimex ADUC-H7020 and Analog Devices EVAL-ADUC7020 as well as in many popular embedded devices.

Consider it a more useable form of the offical ARMWSD-UART.exe program.

General useage:
    ac=AducConnection('COM1')
    if ac.upload('myprogram.hex'):
        ac.run()
Or use the shortcut:
    upload('myprogram.hex','COM1',andRun=True)
"""
import typing
try:
    import serial
except ImportError as e:
    print('pyserial not found.  Try something like\n\tpip install pyserial')
    raise e
try:
    import intelhex
except ImportError as e:
    print('intelhex library (for .hex format) was not found.  Try something like\n\tpip install intelhex')
    raise e


class AducConnection:
    """
    Python interface to the serial uploader for Analog Devices ADuC70xx family of devices.

    This includes the popular ADuC-7020 chip as found in development boards like the
    Olimex ADUC-H7020 and Analog Devices EVAL-ADUC7020 as well as in many popular embedded devices.

    Consider it a more useable form of the offical ARMWSD-UART.exe program.

    General useage:
        ac=AducConnection('COM1')
        if ac.upload('myprogram.hex'):
            ac.run()
    Or use the shortcut:
        upload('myprogram.hex','COM1',andRun=True)
    """

    def __init__(self,
        port:str="COM6",
        baudrate:int=115200,
        bytesize:int=8,
        parity:str='N',
        stopbits:float=1,
        xonxoff:int=0,
        rtscts:int=0):
        """ """
        self.port:str=port
        self.baudrate=baudrate
        self.bytesize=bytesize
        self.parity=parity
        self.stopbits=stopbits
        self.timeout=0.01
        self.xonxoff=xonxoff
        self.rtscts=rtscts
        self.numTries:int=3
        self._connection:typing.Optional[serial.Serial]=None

    def connect(self)->serial.Serial:
        """
        connect the serial port (called automatically as needed)
        """
        if not self._connection:
            self._connection=serial.Serial(self.port,self.baudrate,self.bytesize,self.parity,self.stopbits,self.timeout,self.xonxoff,self.rtscts)
        return self._connection

    def disconnect(self):
        """
        disconnect the serial port (called automatically as needed)
        """
        if self._connection is not None:
            self._connection.close()
            self._connection=None

    def reconnect(self)->serial.Serial:
        """
        Disconnect any existing connection
        and connect.
        """
        self.disconnect()
        return self.connect()

    def _checksum(self,data)->bytes:
        """
        Calculate the checksum of a device packet
        """
        return bytes([0xFF&(0-sum(data))])

    def _sendPacket(self,command:str,address:int,data:bytes)->bool:
        """
        Send a specified command packet to the device
        """
        data:bytearray=bytearray(data) # create a copy to modify
        packet_len=len(data)+5 # 1byte command + 4byte address + the data
        magic:bytes=bytes([0x07,0x0E])
        addr_bytes:bytes=address.to_bytes(length=4,byteorder="little",signed=False)
        data.insert(0,addr_bytes)
        data.insert(0,command.encode('ascii')[0])
        data.insert(0,packet_len)
        checksum=self._checksum(data)
        ser=self.connect()
        # dispose of any lingering incoming crap
        response='x'
        while response:
            response=ser.read(1)
        # send it
        ser.write(magic)
        ser.write(data)
        ser.write(checksum.to_bytes(length=4,byteorder='little',signed=False))
        while not response: 
            response=ser.read(1)
        if response[0]==0x06: # device responded with success
            return True
        if response[0]==0x07: # device responded with fail
            return False
        raise Exception('Unexpected serial response: 0x%02x',response[0])

    def _erasePacket(self,address:int,numPages:int)->bool:
        """
        Send an erase packet to the device
        """
        ret=False
        if numPages<1 or numPages>124:
            raise Exception('numPages must be 1..124 (%d given)'%numPages)
        ret=self._sendPacket('E',address,numPages.to_bytes(1,byteorder='little',signed=False))
        return ret

    def erase(self,address:int,numBytes:int)->bool:
        """
        Erase flash starting at address and ending at address+numBytes
        (will always round up to erase entire pages)
        """
        pageSize=512
        self._erasePacket(address,numBytes//pageSize)

    def _writePacket(self,address:int,data:bytes)->bool:
        """
        Send a write packet to the device
        """
        ret=False
        for _ in range(self.numTries):
            ret=self._sendPacket('W',address,data)
            if ret:
                break
        return ret

    def write(self,address:int,data:bytes,progressCB:typing.Optional[typing.Callable[[float],None]]=None,andVerify=True,andRun=False,andReset=False)->bool:
        """
        Write some data to the device.

        Will also erase, and (optionally) verify, run, and/or reset.
        """
        ret=True
        complete=0
        total=len(data)
        self.erase(address,total)
        while complete<total:
            numWritten=min(total-complete,250)
            ret=self._writePacket(address,data[complete:complete+numWritten])
            if not ret:
                return ret
            complete+=numWritten
            address+=numWritten
            if progressCB is not None:
                pct=complete/total
                if andVerify:
                    pct*=0.66
                progressCB(pct)
        if andVerify:
            def pcb(pct:float):
                if progressCB is not None:
                    progressCB(0.66+0.33*pct)
            ret=self.verify(address,data,pcb)
        if andRun:
            self.run()
        elif andReset:
            self.reset()
        self.disconnect()
        return ret
    
    def upload(self,filename:str,progressCB:typing.Optional[typing.Callable[[float],None]]=None,andVerify=True,andRun=False,andReset=False)->bool:
        """
        Upload an intel hex file(.hex) or a binary file (.bin) to the device
        """
        ihex=intelhex.IntelHex(filename)
        return self.uploadIhex(ihex,progressCB,andVerify,andRun,andReset)

    def _looksLikeIhex(self,data:bytes)->bool:
        """
        determine if the data looks like intel hex format or binary bytes
        """
        if len(data)>=10:
            asc=data[0:10].decode('ascii')
            if asc[0]==':':
                import re
                if re.match(r':[0-9A-Fa-f]{2}\s+[[0-9A-Fa-f]{4,99}',asc) is not None:
                    return True
        return False

    def uploadData(self,
        data:bytes,decodeAsIhex:typing.Optional[bool]=None,
        progressCB:typing.Optional[typing.Callable[[float],None]]=None,
        andVerify=True,andRun=False,andReset=False)->bool:
        """
        Upload raw data or intel hex data to the device

        :decodeAsIhex: whether to decode as intel hex format or as raw bytes
            if not specified, will try to guess based upon the file contents
        """
        if decodeAsIhex is None:
            decodeAsIhex=self._looksLikeIhex(data)
        if decodeAsIhex:
            ihex=intelhex.IntelHex()
            raise NotImplementedError("Need to use stringio here")
        else:
            ihex=intelhex.IntelHex()
            ihex.frombytes(data)
        return self.uploadIhex(ihex,progressCB,andVerify,andRun,andReset)

    def uploadIhex(self,ihex:intelhex.IntelHex,progressCB:typing.Optional[typing.Callable[[float],None]]=None,andVerify=True,andRun=False,andReset=False)->bool:
        """
        Upload an intel hex object to the device
        """
        ret=True
        totalbytes=0
        for start,stop in ihex.segments():
            totalbytes+=stop-start
        uploaded=0
        for start,stop in ihex.segments():
            amt=stop-start
            print('writing %d bytes to 0x%08x'%(amt,start))
            def progcb(pct:float):
                if progressCB is not None:
                    progressCB((uploaded+pct*amt)/totalbytes)
            ret=self.write(start,ihex[start:stop],progcb,andVerify,andRun,andReset)
            if not ret:
                break
            uploaded+=amt
        return ret
    
    def _verifyPacket(self,address:int,data:bytes)->bool:
        """
        Send a verify packet to the device
        """
        ret=False
        for _ in range(self.numTries):
            ret=self._sendPacket('V',address,data)
            if ret:
                break
        return ret

    def _verifyShift(self,data:bytes)->bytes:
        """
        When doing a verify, the bits are rotate-shifted
        """
        return bytes([0xFF & (b << 3 | b >> 5) for b in data])

    def verify(self,address:int,data:bytes,progressCB:typing.Optional[typing.Callable[[float],None]]=None)->bool:
        """
        Verify some data
        """
        ret=True
        data=self._verifyShift(data) 
        complete=0
        total=len(data)
        while complete<total:
            ret=self._verifyPacket(address,data)
            if not ret:
                return ret
            if progressCB is not None:
                pct=complete/total
                progressCB(pct)
        return ret

    def _runPacket(self,address:int)->bool:
        """
        Send a run command packet
        """
        ret=False
        for _ in range(self.numTries):
            ret=self._sendPacket('R',address,bytes())
            if ret:
                break
        return ret
    
    def run(self)->bool:
        """
        Run the program by jumping to the start address
        """
        return self._runPacket(0)
    
    def reset(self)->bool:
        """
        Run the program by causing a reset
        """
        return self._runPacket(1)


def upload(filename:str,port:str='COM6',andVerify=True,andRun=False,andReset=False)->bool:
    """
    shortcut to use AducConnection to upload and optionally verify, run, and/or reset the device
    """
    return AducConnection(port).upload(filename,andVerify=andVerify,andRun=andRun,andReset=andReset)

def uploadBytes(data:bytes,port:str='COM6',andVerify=True,andRun=False,andReset=False)->bool:
    """
    shortcut to use AducConnection to upload and optionally verify, run, and/or reset the device
    """
    return AducConnection(port).uploadBytes(data,andVerify=andVerify,andRun=andRun,andReset=andReset)

ad=AducConnection()
shifted=ad._verifyShift([0x01<<b for b in range(8)])
print(['0x%02x'%s for s in shifted])

print(ad._checksum([0x05,0x52,0x00,0x00,0x00,0x01]))
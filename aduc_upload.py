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

For more info on the protocol, see:
    https://www.analog.com/media/en/technical-documentation/application-notes/AN-724.pdf    
"""
import typing
try:
    import serial
except ImportError as e:
    print('pyserial not found.  Try something like:')
    print('    pip install pyserial')
    raise e
try:
    import intelhex
except ImportError as e:
    print('intelhex library (for .hex format) was not found.  Try something like:')
    print('    pip install intelhex')
    raise e


class AducException(Exception):
    """
    An irrecoverable issue occourred.
    (NOTE: most issues are dealt with by returning False from the command)
    """

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
    
    For more info on the protocol, see:
        https://www.analog.com/media/en/technical-documentation/application-notes/AN-724.pdf
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
        self.pageSize=512
        # According to AN-724 you can send up to 250 bytes per packet,
        # but ARMWSD.exe only sends 16 for some reason
        self.bytesPerWritePacket=16
        self._connection:typing.Optional[serial.Serial]=None
        self._connectionEstablished=False

    def connect(self)->serial.Serial:
        """
        connect the serial port (called automatically as needed)
        """
        if not self._connection:
            self._connection=serial.Serial(
                self.port,self.baudrate,self.bytesize,self.parity,
                self.stopbits,self.timeout,self.xonxoff,self.rtscts)
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

    def waitForConnection(self)->bool:
        """
        Wait for an actual device to respond on the serial port
        """
        if self._connectionEstablished:
            return True
        ser=self.connect()
        print('Wait for connection...')
        response=bytes()
        while not response:
            ser.write(bytes([0x08])) # send backspaces
            response=ser.read(24) # until it responds with its id
            if response and response[0] in (0x07,0x80):
                print('\n****************************\nDevice detected, but not in flash mode.\nPlease reboot in flash mode!\n****************************\n')
        print('  OK! Connected to device:',response.decode('ascii').strip())
        self._connectionEstablished=True
        return True

    def _remapAddress(self,address:int)->int:
        """
        During normal operation, flash is mirrored from 0x0080_0000 to 0x0000_0000
        ARMWSD prefers to write to this for some reason.
        """
        if address>=0x0080000:
            address-=0x0080000
        return address

    def _sendPacket(self,command:str,address:int,data:bytes)->bool:
        """
        Send a specified command packet to the device
        """
        address=self._remapAddress(address)
        packet_len=len(data)+5 # 1byte command + 4byte address + the data
        if packet_len>255:
            raise Exception('Packet size too large!')
        magic:bytes=bytes([0x07,0x0E])
        addr_bytes:bytes=address.to_bytes(length=4,byteorder="big",signed=False)
        sendbuf=bytearray(addr_bytes)
        sendbuf.insert(0,command.encode('ascii')[0])
        sendbuf.insert(0,packet_len)
        sendbuf.extend(data)
        checksum=self._checksum(sendbuf)
        ser=self.connect()
        # dispose of any lingering incoming junk
        response='x'
        while response:
            response=ser.read(1)
        # send it
        ser.write(magic)
        ser.write(sendbuf)
        ser.write(checksum)
        while not response:
            response=ser.read(1)
        if response[0]==0x06: # device responded with success
            print('.',end='')
            return True
        if response[0]==0x07: # device responded with fail
            print('X',end='')
            return False
        raise AducException(f'Unexpected serial response: {hex(response[0])}')

    def _erasePacket(self,address:int,numPages:int)->bool:
        """
        Send an erase packet to the device
        """
        ret=False
        if numPages<1 or numPages>124:
            raise AducException('numPages must be 1..124 (%d given)'%numPages)
        ret=self._sendPacket('E',address,numPages.to_bytes(1,byteorder='little',signed=False))
        return ret

    def erase(self,address:int,numBytes:int)->bool:
        """
        Erase flash starting at address and ending at address+numBytes
        (will always round up to erase entire pages)
        """
        print(f'Erasing {numBytes} bytes at {hex(address)}...',end='')
        ret=self._erasePacket(address,numBytes//self.pageSize)
        if ret:
            print('OK')
        else:
            print('FAIL')
        return ret

    def _writePacket(self,address:int,data:bytes)->bool:
        """
        Send a write packet to the device
        """
        ret=False
        print(f'Write {len(data)} bytes to {hex(address)}...',end='')
        for _ in range(self.numTries):
            ret=self._sendPacket('W',address,data)
            if ret:
                break
        if ret:
            print('OK')
        else:
            print('FAIL')
        return ret

    def write(self,address:int,data:bytes,
        progressCB:typing.Optional[typing.Callable[[float],None]]=None,
        andVerify=True,andRun=False,andReset=False
        )->bool:
        """
        Write some data to the device.

        Will also erase, and (optionally) verify, run, and/or reset
        depending on what control flags you pass in.
        """
        startAddress=address
        ret=True
        complete=0
        total=len(data)
        weConnected=self._connectionEstablished is False
        if weConnected:
            self.waitForConnection()
        self.erase(address,total)
        while complete<total:
            numWritten=min(total-complete,self.bytesPerWritePacket)
            chunk=data[complete:complete+numWritten]
            ret=self._writePacket(address,chunk)
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
            ret=self.verify(startAddress,data,pcb)
        if andRun:
            self.run()
        elif andReset:
            self.reset()
        self.disconnect()
        if weConnected:
            self._connectionEstablished=False
        return ret

    def upload(self,
        filename:str,
        progressCB:typing.Optional[typing.Callable[[float],None]]=None,
        andVerify=True,andRun=False,andReset=False
        )->bool:
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

    def uploadIhex(self,
        ihex:intelhex.IntelHex,
        progressCB:typing.Optional[typing.Callable[[float],None]]=None,
        andVerify=True,andRun=False,andReset=False
        )->bool:
        """
        Upload an intel hex object to the device
        """
        ret=True
        self.waitForConnection()
        totalbytes=0
        for start,stop in ihex.segments():
            totalbytes+=stop-start
        uploaded=0
        for start,stop in ihex.segments():
            amt=stop-start
            def progcb(pct:float):
                if progressCB is not None:
                    progressCB((uploaded+pct*amt)/totalbytes)
            ret=self.write(start,ihex.tobinarray(start,stop),progcb,andVerify,andRun,andReset)
            if not ret:
                break
            uploaded+=amt
        self._connectionEstablished=False
        return ret
    uploadBytes=uploadData

    def _verifyPacket(self,address:int,data:bytes)->bool:
        """
        Send a verify packet to the device
        """
        ret=False
        print(f'Verify {len(data)} bytes at {hex(address)}...',end='')
        for _ in range(self.numTries):
            ret=self._sendPacket('V',address,data)
            if ret:
                break
        if ret:
            print('OK')
        else:
            print('FAIL')
        return ret

    def _verifyShift(self,data:bytes)->bytes:
        """
        When doing a verify, the bits are rotate-shifted
        """
        return bytes([0xFF & (b << 3 | b >> 5) for b in data])

    def verify(self,
        address:int,
        data:bytes,
        progressCB:typing.Optional[typing.Callable[[float],None]]=None
        )->bool:
        """
        Verify some data
        """
        ret=True
        data=self._verifyShift(data)
        complete=0
        total=len(data)
        weConnected=self._connectionEstablished is False
        if weConnected:
            self.waitForConnection()
        while complete<total:
            numVerified=min(total-complete,self.bytesPerWritePacket)
            chunk=data[complete:complete+numVerified]
            ret=self._verifyPacket(address,chunk)
            if not ret:
                return ret
            complete+=numVerified
            address+=numVerified
            if progressCB is not None:
                pct=complete/total
                progressCB(pct)
        if weConnected:
            self.disconnect()
            self._connectionEstablished=False
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
        print('Running...',end='')
        ret=self._runPacket(0)
        if ret:
            print('OK')
        else:
            print('FAIL')
        return ret

    def reset(self)->bool:
        """
        Run the program by causing a reset
        """
        print('Resetting...',end='')
        ret=self._runPacket(1)
        if ret:
            print('OK')
        else:
            print('FAIL')
        return ret


def upload(filename:str,port:str='COM6',andVerify=True,andRun=False,andReset=False)->bool:
    """
    shortcut to use AducConnection to upload and optionally verify, run, and/or reset the device
    """
    return AducConnection(port).upload(filename,
        andVerify=andVerify,andRun=andRun,andReset=andReset)


def uploadBytes(data:bytes,port:str='COM6',andVerify=True,andRun=False,andReset=False)->bool:
    """
    shortcut to use AducConnection to upload and optionally verify, run, and/or reset the device
    """
    return AducConnection(port).uploadBytes(data,
        andVerify=andVerify,andRun=andRun,andReset=andReset)


def cmdline(args:typing.Iterable[str])->int:
    """
    Run the command line

    :param args: command line arguments (WITHOUT the filename)
    """
    didSomething=False
    printhelp=False
    filename=''
    port:str='COM6'
    andVerify=True
    andRun=False
    andReset=False
    worked=False
    for arg in args:
        if arg.startswith('-'):
            av=arg.split('=',1)
            av[0]=av[0].lower()
            if av[0] in ('-h','--help'):
                printhelp=True
            elif av[0]=='--port':
                port=av[1].strip()
            elif av[0]=='--verify':
                andVerify=len(av)<2 or av[1][0].lower() in ('t','y','1')
            elif av[0]=='--run':
                andRun=len(av)<2 or av[1][0].lower() in ('t','y','1')
            elif av[0]=='--reset':
                andReset=len(av)<2 or av[1][0].lower() in ('t','y','1')
            else:
                printhelp=True
        else:
            filename=arg
    if not printhelp and filename and port:
        def progressCB(pct:float):
            WIDTH=78
            blocks=int(pct*WIDTH)
            filled='#'*blocks
            empty='_'*(WIDTH-blocks)
            #print(f'\r[{filled}{empty}]')
        print()
        if filename=='STDIN':
            data=sys.stdin.read().encode('ascii')
            worked = AducConnection(port).uploadBytes(data,
                progressCB=progressCB,andVerify=andVerify,andRun=andRun,andReset=andReset)
        else:
            worked = AducConnection(port).upload(filename,
                progressCB=progressCB,andVerify=andVerify,andRun=andRun,andReset=andReset)
        didSomething=True
    if printhelp or not didSomething:
        print('USEAGE:')
        print('  py_aduc_upload [options] [filename]')
        print('OPTIONS:')
        print('  -h ............... this help')
        print('  --port= .......... serial port (what your os calls it, eg "COM1" or "/dev/ttyS0")')
        print('  --run[=t/f]  ..... auto-run after uploading (default = f)')
        print('  --reset[=t/f]  ... reset device after uploading (default = f)')
        print('  --verify[=t/f]  .. verify after uploading (default = t)')
        print('FILENAME:')
        print('  If the filename is STDIN it will read the file bytes from standard i/o')
        return 1
    if worked:
        print('SUCCESS')
        return 0
    print('FAIL')
    return -1


if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))
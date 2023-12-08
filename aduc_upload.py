#!/usr/bin/env python3
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
import os
import subprocess
from math import ceil
from enum import Enum, auto
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

class AducStatus(Enum):
    """
    Status of a device connection
    """
    CONNECTING=auto()
    PORT_IN_USE=auto()
    WAITING_FOR_DEVICE=auto()
    NOT_IN_FLASH_MODE=auto()
    DEVICE_FOUND=auto()
    ERASING=auto()
    ERASE_FAILED=auto()
    ERASE_SUCCEEDED=auto()
    WRITING=auto()
    WRITE_FAILED=auto()
    WRITE_SUCCEEDED=auto()
    VERIFYING=auto()
    VERIFY_FAILED=auto()
    VERIFY_SUCCEEDED=auto()
    RUNNING=auto()
    RUN_FAILED=auto()
    RUN_SUCCEEDED=auto()
    RESETTING=auto()
    RESET_FAILED=auto()
    RESET_SUCCEEDED=auto()
    POST_STEP=auto()
    POST_STEP_SUCCEEDED=auto()
    POST_STEP_FAILED=auto()
    DONE=auto()

StatusCB=typing.Callable[[AducStatus],None]
PercentCB=typing.Callable[[float],None]

class StdoutCB:
    """
    default status output (dump to stdout)
    """
    def __init__(self):
        self.percent=0
        self.status:str=""
        self.last:str=""
    def statusCB(self,status:AducStatus)->None:
        """
        Callback for a status state change
        """
        self.status=' '.join([word.lower() for word in str(status).rsplit('.',1)[-1].split('_')])
        current=str(self)+' '*20
        if current!=self.last:
            print(current,end="")
            self.last=current
    def percentCB(self,percent:float)->None:
        """
        Callback for a percent complete change
        """
        self.percent=percent
        current=str(self)+' '*20
        if current!=self.last:
            print(current,end="")
            self.last=current
    def __repr__(self):
        width=50
        full=int(width*self.percent)
        statusbar='#'*full+'_'*(width-full)
        return f'\r[{statusbar}] {self.status}'
stdoutCB=StdoutCB()


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
        rtscts:int=0,
        statusCB:StatusCB=stdoutCB.statusCB,
        percentCB:PercentCB=stdoutCB.percentCB
        ):
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
        self.statusCB:StatusCB=statusCB
        self.percentCB:PercentCB=percentCB
        self._connection:typing.Optional[serial.Serial]=None
        self._connectionEstablished=False

    def connect(self)->serial.Serial:
        """
        connect the serial port (called automatically as needed)
        """
        if not self._connection:
            self.statusCB(AducStatus.CONNECTING)
            self.percentCB(0)
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

    def waitForDevice(self)->bool:
        """
        Wait for an actual device to respond on the serial port
        """
        if self._connectionEstablished:
            return True
        ser=self.connect()
        self.statusCB(AducStatus.WAITING_FOR_DEVICE)
        self.percentCB(0)
        response=bytes()
        while not response:
            ser.write(bytes([0x08])) # send backspaces
            response=ser.read(24) # until it responds with its id
            if response and response[0] in (0x07,0x80):
                self.statusCB(AducStatus.NOT_IN_FLASH_MODE)
        self.statusCB(AducStatus.DEVICE_FOUND)
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
            return True
        if response[0]==0x07: # device responded with fail
            return False
        raise AducException(f'Unexpected serial response: {hex(response[0])}')

    def _erasePacket(self,address:int,numPages:int)->bool:
        """
        Send an erase packet to the device
        """
        ret=False
        if numPages<1 or numPages>124:
            if numPages==0:
                return True # because, sure, I erased zero pages.
            raise AducException('numPages must be 1..124 (%d given)'%numPages)
        ret=self._sendPacket('E',address,numPages.to_bytes(1,byteorder='little',signed=False))
        return ret

    def erase(self,address:int,numBytes:int)->bool:
        """
        Erase flash starting at address and ending at address+numBytes
        (will always round up to erase entire pages)
        """
        if numBytes<1:
            return True
        self.statusCB(AducStatus.ERASING)
        ret=self._erasePacket(address,ceil(numBytes/self.pageSize))
        if not ret:
            self.statusCB(AducStatus.ERASE_FAILED)
        else:
            self.statusCB(AducStatus.ERASE_SUCCEEDED)
            self.percentCB(1.0)
        return ret
        
    def massErase(self)->bool:
        """
        Erase the entire flash
        (and un-protect)

        IMPORTANT NOTE:  Erases entire flash, so will also
            lose config data section too!
        """
        self.statusCB(AducStatus.ERASING)
        ret=self._erasePacket(0x00000000,0x00)
        if not ret:
            self.statusCB(AducStatus.ERASE_FAILED)
        else:
            self.statusCB(AducStatus.ERASE_SUCCEEDED)
            self.percentCB(1.0)
        return ret
    eraseAll=massErase

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

    def write(self,address:int,data:bytes,
        andVerify=True,andRun=False,andReset=False,noErase=False
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
        if total<=0:
            raise AducException("No data given!")
        print(f"Uploading {total} bytes ({ceil(total/self.pageSize)} pages)")
        weConnected=self._connectionEstablished is False
        if weConnected:
            self.waitForDevice()
        if not noErase:
            self.erase(address,total)
        self.statusCB(AducStatus.WRITING)
        self.percentCB(0.0)
        while complete<total:
            numWritten=min(total-complete,self.bytesPerWritePacket)
            chunk=data[complete:complete+numWritten]
            while len(chunk)<self.bytesPerWritePacket:
                chunk.append(0x00)
            ret=self._writePacket(address,chunk)
            if not ret:
                self.statusCB(AducStatus.WRITE_FAILED)
                return ret
            self.percentCB(complete/total)
            complete+=numWritten
            address+=numWritten
        self.statusCB(AducStatus.WRITE_SUCCEEDED)
        self.percentCB(1.0)
        if andVerify:
            ret=self.verify(startAddress,data)
        if andRun:
            self.run()
        elif andReset:
            self.reset()
        self.disconnect()
        if weConnected:
            self._connectionEstablished=False
        return ret

    def _elfFileToIhexFile(self,filename:str)->str:
        """
        Convert a .elf file into a .hex file
        """
        ihexFilename=filename.rsplit('.',1)[0]+'.hex'
        if not os.path.exists(ihexFilename) or os.path.getmtime(filename)>os.path.getmtime(ihexFilename):
            # (re)generate the ihexFilename file
            cmd=['objcopy','-S','-O','ihex',filename,ihexFilename]
            po=subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            _,err=po.communicate()
            err=err.decode('utf-8',errors='ignore').strip()
            if err:
                raise AducException('Error converting .elf to .hex: '+err)
        return ihexFilename

    def loadIhex(self,filename:str)->intelhex.IntelHex:
        """
        Load an intel .hex file
        """
        extn=filename.rsplit('.',1)[-1].lower()
        if extn=='elf':
            filename=self._elfFileToIhexFile(filename)
        return intelhex.IntelHex(filename)

    def upload(self,
        filename:str,
        andVerify:bool=True,andRun:bool=False,andReset:bool=False,
        postRun:typing.Optional[str]=None
        )->bool:
        """
        Upload an intel hex file(.hex), elf linker output (.elf) or
        a binary file (.bin) to the device
        """
        ihex=self.loadIhex(filename)
        return self.uploadIhex(ihex,andVerify,andRun,andReset,postRun)

    def _looksLikeIhex(self,data:bytes)->bool:
        """
        determine if the data looks like intel hex format
        """
        if len(data)>=10:
            asc=data[0:10].decode('ascii')
            if asc[0]==':':
                import re
                if re.match(r':[0-9A-Fa-f]{2}\s+[[0-9A-Fa-f]{4,99}',asc) is not None:
                    return True
        return False

    def _looksLikeElf(self,data:bytes)->bool:
        """
        determine if the data looks like elf format
        """
        if len(data)>=4:
            asc=data[1:4].decode('ascii')
            return asc==b'ELF'
        return False

    def uploadData(self,
        data:bytes,decodeAs:typing.Optional[str]=None,
        andVerify=True,andRun=False,andReset=False)->bool:
        """
        Upload raw data or intel hex data to the device

        :decodeAs: whether to decode as 'ihex' (intel hex) format, 'elf', or as 'raw' bytes
            if not specified, will try to guess based upon the file contents
        """
        if decodeAs is None:
            if self._looksLikeIhex(data):
                decodeAs='ihex'
            elif self._looksLikeElf(data):
                decodeAs='elf'
            else:
                decodeAs='raw'
        else:
            decodeAs=decodeAs.lower()
        if decodeAs in ('ihex','hex'):
            ihex=intelhex.IntelHex()
            raise NotImplementedError("Need to use stringio here")
        elif decodeAs=='elf':
            raise NotImplementedError("decode elf bytes!")
        else:
            ihex=intelhex.IntelHex()
            ihex.frombytes(data)
        return self.uploadIhex(ihex,andVerify,andRun,andReset)

    def uploadIhex(self,
        ihex:intelhex.IntelHex,
        andVerify:bool=True,andRun:bool=False,andReset:bool=False,
        postRun:typing.Optional[str]=None
        )->bool:
        """
        Upload an intel hex object to the device
        """
        ret=True
        if postRun is not None:
            postRun=postRun.strip()
            if not postRun:
                postRun=None
        self.waitForDevice()
        totalbytes=0
        for start,stop in ihex.segments():
            totalbytes+=stop-start
        # erase
        for start,stop in ihex.segments():
            self.erase(start,stop-start)
        # write
        uploaded=0
        for start,stop in ihex.segments():
            amt=stop-start
            # wait until after this loop to do run/reset in case there is more than 1 segment
            ret=self.write(start,ihex.tobinarray(start,stop),andVerify,False,False,noErase=True)
            if not ret:
                break
            uploaded+=amt
        if ret:
            if andRun:
                ret=self.run()
            elif andReset:
                ret=self.reset()
            # we resetted, so don't consider firmware update mode "connected" anymore
            self._connectionEstablished=False
        if ret and (postRun is not None):
            # run whatever the postRun shell command is
            self.statusCB(AducStatus.POST_STEP)
            self.percentCB(0.0)
            po=subprocess.Popen(postRun,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            out,_=po.communicate()
            print(out.decode('utf-8',errors='ignore').strip())
            ret=po.returncode!=0
            if ret:
                self.statusCB(AducStatus.POST_STEP_SUCCEEDED)
                self.percentCB(1.0)
            else:
                self.statusCB(AducStatus.POST_STEP_FAILED)
        return ret
    uploadBytes=uploadData

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

    def verify(self,
        address:int,
        data:bytes
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
            self.waitForDevice()
        self.statusCB(AducStatus.VERIFYING)
        self.percentCB(0.0)
        while complete<total:
            numVerified=min(total-complete,self.bytesPerWritePacket)
            chunk=data[complete:complete+numVerified]
            ret=self._verifyPacket(address,chunk)
            if not ret:
                self.statusCB(AducStatus.VERIFY_FAILED)
                return ret
            complete+=numVerified
            address+=numVerified
            self.percentCB(complete/total)
        if weConnected:
            self.disconnect()
            self._connectionEstablished=False
        self.statusCB(AducStatus.VERIFY_SUCCEEDED)
        self.percentCB(1.0)
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
        self.statusCB(AducStatus.RUNNING)
        self.percentCB(0.0)
        ret=self._runPacket(0)
        if ret:
            self.statusCB(AducStatus.RUN_SUCCEEDED)
            self.percentCB(1.0)
        else:
            self.statusCB(AducStatus.RUN_FAILED)
        return ret

    def reset(self)->bool:
        """
        Run the program by causing a reset
        """
        self.statusCB(AducStatus.RESETTING)
        self.percentCB(0.0)
        ret=self._runPacket(1)
        if ret:
            self.statusCB(AducStatus.RESET_SUCCEEDED)
            self.percentCB(1.0)
        else:
            self.statusCB(AducStatus.RESET_FAILED)
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
    postRun=None
    massEraseFirst=False
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
            elif av[0]=='--thenrun':
                postRun=av[1].strip()
            elif av[0] in ('--masserase','--eraseall'):
                massEraseFirst=True
            else:
                printhelp=True
        else:
            filename=arg
    if not printhelp and (filename or massEraseFirst) and port:
        print()
        aduc=AducConnection(port)
        if massEraseFirst:
            aduc.massErase()
        if filename=='STDIN':
            data=sys.stdin.read().encode('ascii')
            worked = aduc.uploadBytes(data,
                andVerify=andVerify,andRun=andRun,andReset=andReset)
        elif filename:
            worked = aduc.upload(filename,
                andVerify=andVerify,andRun=andRun,andReset=andReset,postRun=postRun)
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
        print('  --postRun="shell command"  .. run a shell command after the upload')
        print('  --massErase ...... erase (and unprotect) entire flash before upload')
        print('  --eraseAll ....... same as --massErase')
        print('FILENAME:')
        print('  accepts .hex, .elf, and .bin')
        print('  If the filename is STDIN it will read the file bytes from standard i/o')
        return 1
    if worked:
        print('\nSUCCESS')
        return 0
    print('\nFAIL')
    return -1

if __name__=='__main__':
    import sys
    sys.exit(cmdline(sys.argv[1:]))
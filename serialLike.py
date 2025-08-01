"""
Anything that looks and smells like a pyserial Serial object
"""
import typing


class SerialLike(typing.Protocol):
    """
    Anything that looks and smells like a pyserial Serial object
    """
    is_open:bool
    in_waiting:int
    out_waiting:int

    @property
    def name(self)->str:
        """
        Serial device name eg, "COM5"
        """
        raise NotImplementedError()

    @property
    def baudrate(self)->int:
        """
        The current baud rate
        """
        raise NotImplementedError()

    def __init__(self,port:str,baudRate:int):
        pass

    def reset_input_buffer(self):
        """
        Clear any pending read data
        """

    def reset_output_buffer(self):
        """
        Clear any pending write data
        """

    def write(self,data:bytes)->int:
        """
        Write data
        """
        raise NotImplementedError()

    def read(self,n:typing.Optional[int]=None)->bytes:
        """
        Read data
        """
        raise NotImplementedError()

    def close(self):
        """
        close the port
        """

    def flush(self):
        """
        flush the write buffer
        """

"""
Anything that looks and smells like a pyserial Serial object
"""
import typing


class SerialLike(typing.Protocol):
    """
    Anything that looks and smells like a pyserial Serial object
    """
    name:str
    is_open:bool
    in_waiting:int
    out_waiting:int

    def reset_input_buffer(self):
        """
        Clear any pending read data
        """

    def reset_output_buffer(self):
        """
        Clear any pending write data
        """

    def write(self,data:bytes):
        """
        Write data
        """

    def read(self,n:typing.Optional[int]=None)->bytes:
        """
        Read data
        """

    def close(self):
        """
        close the port
        """

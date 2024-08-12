"""
Tools to help identify what type of device is connected
to a particular port
"""
import typing
from py_aduc_upload.serialLike import SerialLike


PortValidationFunction=typing.Callable[
    [SerialLike,typing.Unpack[...]], # type: ignore
    typing.Optional[typing.Any]]

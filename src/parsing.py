from csv import reader
from typing import List
from serial import Serial
from logging import debug

from config import Config
from firmware import Firmware
from debug import __FILE__, __LINE__
from dataclasses import dataclass, field
from serial_port import SerialTimeoutError

class EmptyLineError(Exception):
    """Custom exception to signal an empty line from serial data"""
    pass


@dataclass
class Data:
    line_count: int;
    header_parsed: bool;
    header: list = field(default_factory=list[str]);
    col_index: dict = field(default_factory=dict);
    line: str = field(init=False);
    firmware_type: Firmware = field(init=False);

    
    def getline(self, ser: Serial, conf: Config) -> (str|None):
        """get the serial line """
        response: bytes = ser.readline()
        if not response:
            debug(f"{__FILE__()}:{__LINE__()} No response from serial port.")
            if self.line_count > conf.max_lines and not self.header_parsed:
                raise SerialTimeoutError(
                    "Timeout waiting for header. check ESP connnection"
                )
            return (None);
        _line: str = response.decode("utf-8", errors="ignore")
        self.line: str = _line.strip()
        print(f"line:{self.line}")
        if not self.line:
            raise EmptyLineError("Recieved empty line")
        self.line_count += 1
        return (self.line);


    def __find_header(self) -> List:
        """"""
        try:
            if self.line and self.line.startswith("type,"):
                self.header = next(reader([self.line]))
                return (self.header);
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e


    # There is a line in cpu_start that contains the project name, it might
    # be useful for detecting firmware type
    # this function is incorrect, so what we should do is
    # we indicate that the header is parsed if it was found by self.__find_header()
    # but we keeps the firmware not found
    # then in the first csi data line, we take the indicator 
    # and we detact the firmware from it (try to make it parallel to other calculation
    # steps)
    def detect_firmware_type(self, conf: Config) -> str:
        """Detects firmware type based on the first line."""
        _line = next(reader([self.line]))
        try:
            self.firmware_type = conf.firmwares[_line[0]]
        except KeyError:
            self.firmware_type = "unknown"


    def parse_header(self):
        """Returns 0 on successful parsing and -1 on error"""
        try:
            self.__find_header()
            if self.header:
                self.col_index = {name: i for i, name in enumerate(self.header)}
                self.header_parsed = True
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e

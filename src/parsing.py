import re
from csv import reader
from typing import List

from config import Config
from firmware import Firmware
from debug import __FILE__, __LINE__
from dataclasses import dataclass, field

class EmptyLineError(Exception):
    """Custom exception to signal an empty line from serial data"""
    pass


@dataclass
class Data:
    line_count: int
    header_parsed: bool
    header: list = field(default_factory=list[str])
    col_index: dict = field(default_factory=dict)
    firmware_type: Firmware = field(default_factory=Firmware)
    line: str = field(init=False)
    firmware_ded: bool = field(default=False)

    
    def decodeline(self, raw_response: bytes):
        """get the serial line """
        _line: str = raw_response.decode("utf-8", errors="ignore")
        self.line: str = _line.strip()
        if not self.line:
            raise EmptyLineError("Recieved empty line")
        self.line_count += 1
        return ;
        # return (self.line);


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
    def detect_firmware_type(self, conf: Config):
        """Detects firmware type based on the first line."""
        try:
            if self.line and "cpu_start: Project name:" in self.line:
                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])') # add the regex to the config file
                clean_line = ansi_escape.sub('', self.line).strip()
                clean_line = clean_line.split(" ")
                if 'csi' or 'passive' in clean_line:
                    self.firmware_type = conf.firmwares[clean_line[-1]]
                self.firmware_ded = True;
        except KeyError:
            self.firmware_type.name = "unknown"


    def parse_header(self):
        """Returns 0 on successful parsing and -1 on error"""
        try:
            if self.firmware_type.data_header == False:
                self.header_parsed = True
                return ;
            self.__find_header()
            if self.header:
                self.col_index = {name: i for i, name in enumerate(self.header)}
                self.header_parsed = True
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e
        
    def parsed_tracking_rules(self, conf: Config) -> bool:
        if not self.firmware_ded:
            self.detect_firmware_type(conf)
        self.parse_header()
        if self.header_parsed:
            return (True);
        return (False);

    def get_esp_ts(self) -> int:
        esp_ts = None
        fields = self.line.split(self.firmware_type.delimater)
        if fields:
            try:
                if (self.firmware_type.timestamp_label == "last_value"):
                    esp_ts = int(fields[-2].strip())
                else:
                    idx = self.col_index[self.firmware_type.timestamp_label]
                    esp_ts = int(fields[idx].strip())
            except (ValueError, IndexError):
                pass
        return (esp_ts);

    def get_line_kind(self) -> str:
        """
        Classifies the current line payload to determine its routing destination.
        Returns: "resources", "metrics", or "noise"
        """
        if not self.line:
            return "noise"
        
        lower_line = self.line.lower()
        if "resmon:" in lower_line or "cpu:" in lower_line:
            return "resources"
        # If it doesn't look like an explicit resource line, assume it's potential CSI data
        return "metrics"

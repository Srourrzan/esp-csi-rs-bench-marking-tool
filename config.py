from datetime import datetime
from typing import TypedDict, Dict
from pydantic import BaseModel, PrivateAttr
from serial_port import find_port

# --- Configuration ---
LOG_DIR = "logs"
CSV_DIR = "data_logs" # Separate directory for CSV data
CSV_FILE_PREFIX = "csi_latency_data_"
STATS_FILE_PREFIX = "csi_latency_stats_"

# Use a timestamp for unique file names
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILENAME = f"{CSV_DIR}/{CSV_FILE_PREFIX}{TIMESTAMP}.csv"
STATS_FILENAME = f"{CSV_DIR}/{STATS_FILE_PREFIX}{TIMESTAMP}.csv"

class Config(BaseModel):
    __usb_port: str = PrivateAttr();
    __baud_rate: int = PrivateAttr();
    __output_csv_file: str = PrivateAttr();
    __task: str = PrivateAttr();
    __valid_tasks: list[str] = PrivateAttr();

    @property
    def usb_port(self) -> str:
        return self.__usb_port

    @property
    def baud_rate(self) -> int:
        return self.__baud_rate

    @property
    def output_csv_file(self) -> str:
        return self.__output_csv_file

    @property
    def task(self):
        return self.__task

    @property
    def valid_tasks(self):
        return self.__valid_tasks

    @usb_port.setter
    def usb_port(self, value: str = None):
        if value is not None:
            raise ValueError("Should not pass value to usb_port.");
        value = find_port()
        if not value:
            raise ValueError("No valid USB port was found.");
        self.__usb_port = value;
        return ;
    # @baud_rate.setter
    # def baud_rate(self, value: int):
    #     self.__baud_rate = value

    # @output_csv_file.setter
    # def output_csv_file(self, value: str):
    #     self.__output_csv_file = value

    def validate_configs(self, json_configs: Dict) -> int:
        """"""
        conf.__baud_rate = json_configs["baud_rate"]
        if not conf.__baud_rate:
            return (-1);
        conf.__output_csv_file = json_configs["output_csv_file"]
        if not conf.__output_csv_file:
            return (-1);
        conf.__task = json_configs["task"]
        if not conf.__task:
            return (-1);
        conf.__valid_tasks = json_configs["output_csv_file"]
        if not conf.__valid_tasks:
            return (-1);
        return (0);

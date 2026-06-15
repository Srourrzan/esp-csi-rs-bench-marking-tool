import json5
from sys import stderr
from typing import Dict
from pathlib import Path
from os.path import join
from pydantic import BaseModel, PrivateAttr
from logging import FileHandler, StreamHandler, basicConfig

from firmware import Firmware
from queue_config import QueueConfig
from debug import __FILE__, __LINE__

class Config(BaseModel):
    run_ts: str;
    __run_seconds: int = PrivateAttr();
    __usb_port: str = PrivateAttr();
    __baud_rate: int = PrivateAttr();
    __timeout: int = PrivateAttr();
    __output_csv_file: str = PrivateAttr();
    __task: str = PrivateAttr();
    __valid_tasks: list[str] = PrivateAttr();
    __log_dir: str = PrivateAttr();
    __log_level: str = PrivateAttr();
    __csv_dir: str = PrivateAttr();
    __csv_file_prefix: str = PrivateAttr();
    __stats_file_prefix: str = PrivateAttr();
    __max_lines: str = PrivateAttr();
    __firmwares: Dict[str, Firmware] = PrivateAttr();
    __queue_config: QueueConfig = PrivateAttr();

    @property
    def run_seconds(self) -> int:
        return (self.__run_seconds);

    # @run_seconds.setter
    # def run_seconds(self, value: int = 0):
    #     self.__run_seconds = value
    #     return ;

    @property
    def usb_port(self) -> str:
        return (self.__usb_port);

    @usb_port.setter
    def usb_port(self, value: str = None):
        self.__usb_port = value
        return ;
    
    @property
    def baud_rate(self) -> int:
        return (self.__baud_rate);

    @property
    def timeout(self) -> int:
        return (self.__timeout);
    
    @property
    def output_csv_file(self) -> str:
        return (self.__output_csv_file);

    @property
    def task(self) -> str:
        return (self.__task);

    @property
    def valid_tasks(self) -> list[str]:
        return (self.__valid_tasks);

    @property
    def log_dir(self) -> str:
        return (self.__log_dir);

    @property
    def csv_dir(self) -> str:
        return (self.__csv_dir);

    @property
    def csv_file_prefix(self) -> str:
        return (self.__csv_file_prefix);

    @property
    def stats_file_prefix(self) -> str:
        return (self.__stats_file_prefix);

    @property
    def max_lines(self) -> int:
        return (self.__max_lines);

    @property
    def csv_filename(self) -> str:
        csv_file = join(self.__csv_dir,
                        f"{self.__csv_file_prefix}{self.run_ts}.csv")
        return (csv_file);

    @property
    def stats_filename(self) -> str:
        stats_file = join(self.__csv_dir,
                          f"{self.__stats_file_prefix}{self.run_ts}.csv")
        return (stats_file);

    @property
    def firmwares(self) -> Dict[str, Firmware]:
        return (self.__firmwares);

    @property
    def queue_config(self) -> QueueConfig:
        return (self.__queue_config);

    
    def __validate_firmwares(self, json_configs: Dict):
        self.__firmwares= {}
        if "firmware_types" not in json_configs:
            raise ValueError (
                f"{__FILE__()}:{__LINE__()}: firmware types are not set"
            )
        for indicator, properties in json_configs["firmware_types"].items():
            firmware = Firmware.from_dict(properties)
            self.__firmwares[indicator] = firmware

    def __queue_conf(self, json_configs: Dict):
        self.__queue_config = QueueConfig.from_dict(json_configs["queue_config"])
            
    def __serial_port_conf(self, json_configs: Dict):
        self.__baud_rate = json_configs["baud_rate"]
        if not self.__baud_rate:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: baud rate was not set"
            )
        self.__timeout = json_configs["timeout"]
        if not self.__timeout:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: baud rate was not set"
            )
        

    def __logging_conf(self, json_configs: Dict):
        """"""
        self.__output_csv_file = json_configs["output_csv_file"]
        if not self.__output_csv_file:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: output csv file name was not set"
            )
        self.__log_dir = json_configs["log_dir"]
        if not self.__log_dir:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: log directory was not set"
            )
        self.__log_level = json_configs["log_level"]
        if not self.__log_level:
            self.__log_level = "INFO"
        self.__csv_dir = json_configs["csv_dir"]
        if not self.__csv_dir:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: csv directory was not set"
            )
        self.__csv_file_prefix = json_configs["csv_file_prefix"]
        if not self.__csv_file_prefix:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: csv file prefix was not set"
            )
        self.__stats_file_prefix = json_configs["stats_file_prefix"]
        if not self.__stats_file_prefix:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: stats file prefix was not set"
            )

        
    def validate_configs(self, json_configs: Dict) -> int:
        """"""
        self.__run_seconds = json_configs["run_seconds"]
        if not self.__run_seconds:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: run seconds was not set"
            )
        self.__task = json_configs["task"]
        if not self.__task:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: task type was not set"
            )
        self.__valid_tasks = json_configs["valid_tasks"]
        if not self.__valid_tasks:
            raise ValueError(
                f"{__FILE__()}:{__LINE__()}: valid task types was not set"
            )
        self.__max_lines = json_configs["max_lines"]
        if not self.__max_lines:
            self.__max_lines = 500
            print(f"setting max lines before header timeout to 500")
        try:
            self.__serial_port_conf(json_configs=json_configs)
            self.__logging_conf(json_configs=json_configs)
            self.__validate_firmwares(json_configs=json_configs)
            self.__queue_conf(json_configs=json_configs)
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()}: runtime error from {e}"
            ) from e
        return (0);

    def setup_logging(self) -> int:
        """"""
        try:
            basicConfig(
                level=self.__log_level,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    # FileHandler(log_filename),
                    StreamHandler()
                ]
            )
        except Exception as e:
            print(f"{__FILE__()}:{__LINE__()}, Unexpected error: {e}",
                  file=stderr)
            return (-1);
        return (0);
        
        
# make the config file be passed a cmd arg
def load_config() -> (int, Dict|None):
    try:
        with open("config.jsonc", "r", encoding="utf-8") as file:
            config: Dict = json5.load(file)
    except json5.JSONDecodeError as e:
        print(f"{__FILE__()}:{__LINE__()}: Failed to decode JSON: {e}",
              file=stderr)
        return (-1, None);
    except FileNotFoundError as e:
        print(f"{__FILE__()}:{__LINE__()}: Config.json file was not found: {e}",
              file=stderr)
        return (-1, None);
    return (0, config);

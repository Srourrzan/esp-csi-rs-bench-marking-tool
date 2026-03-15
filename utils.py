import subprocess;
from typing import Dict;
from time import time_ns;
from sys import exit, stderr;
from datetime import datetime;
from serial_port import find_port;

from inspect import currentframe, getframeinfo

from config import Config, load_config
from serial_port import find_port
from debug import __FILE__, __LINE__


def check_ntp_sync() -> bool:
        """
        :return: Returns True if the host system clock is 
        NTP-synchronized.
        :rtype: bool
        """
        try:
                out = subprocess.check_output(["timedatectl"], text=True)
                return ("System clock synchronized: yes" in out);
        except Exception as e:
                print(f"{__FILE__()}:{__LINE__()}: Warning: couldn't verify NTP state: {e}", file=stderr)
                return (False);


def detect_firmware_type(line_content: str) -> (str, str|None):
    """Detects firmware type based on the first line."""
    if line_content.startswith("type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,secondary_channel,local_timestamp,esp_epoch_us,ant,sig_len,rx_state,len,first_word,data"):
        return "Espressif CSI", "CSI_DATA"
    return "Unknown Firmware", None


def now_epoch_us() -> int:
        """
        :return: Returns current epoch time in microseconds (int64).
        :rtype: int
        """
        return (time_ns() // 1000);


def validate_sys() -> (int, Config):
        """
        Docstring for validate_sys

        :return: Description
        :rtype: Any
        """
        status = int
        json_configs: Dict

        try:
                timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
                conf: Config = Config(run_ts = timestamp)
                conf.usb_port = find_port()
                status, json_configs = load_config()
                if (status < 0):
                        return (-1, None);
                conf.validate_configs(json_configs)
        except ValueError as e:
                print(f"{e}", file=stderr)
                return (-1, None);
        except Exception as e:
                print(f"{__FILE__()}:{__LINE__()}, Unexpected error: {e}", file=stderr)
                return (-1, None);
        return (0, conf);


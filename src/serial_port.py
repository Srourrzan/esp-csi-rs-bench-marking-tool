from sys import stderr;
from time import sleep;
from serial import Serial;
from serial.tools import list_ports;
from csv import reader
from typing import List

from debug import __FILE__, __LINE__;
from config import Config;


class SerialTimeoutError(Exception):
    """Custom exception to signal a timeout waiting for serial data."""
    pass


def find_port() -> str:
    ports: list;
    port: str = None;

    ports = list_ports.comports();
    for port_ in ports:
        if ((port_.description != "n/a") and (
                "/dev/ttyUSB" in port_.device or "COM" in port_.device)
            ):
            print(f"{port_.device} is found");
            port = port_.device;
            break;
    if port is None:
        raise ValueError(
            f"{__FILE__()}:{__LINE__()}: No valid USB port was found."
        )
    return (port);

def init_serial(serial: Serial):
    serial.dtr: bool = False
    serial.rts: bool = False
    sleep(0.04)
    serial.reset_input_buffer()
    return ;



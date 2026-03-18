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


class EmptyLineError(Exception):
    """Custom exception to signal an empty line from serial data"""
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

def getline(ser: Serial, conf: Config,
            line_count: int, header_parsed: bool) -> (str, int):
    """get the serial line """
    response: bytes = ser.readline()
    if not response:
        debug("No response from serial port.")
        if line_count > conf.max_lines and not header_parsed:
            raise SerialTomeoutError(
                "Timeout waiting for header. check ESP connnection"
            )
        return (None, line_count);
    line: str = response.decode("utf-8", errors="ignore")
    line: str = line.strip()
    print(f"line:{line}")
    if not line:
        raise EmptyLineError("Recieved empty line")
    line_count += 1
    return (line, line_count);

def find_header(line: str) -> List:
    """"""
    try:
        if line and line.startswith("type,"):
            header: List = next(reader([line]))
            return (header);
    except Exception as e:
        raise RuntimeError(
            f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
        ) from e

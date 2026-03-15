from sys import stderr;
from time import sleep;
from serial import Serial;
from serial.tools import list_ports;

from debug import __FILE__, __LINE__;
from config import Config;

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
    sleep(0.1)
    serial.reset_input_buffer()
    return ;

def getline(ser: Serial, conf: Config, line_count: int) -> (str, int):
    """get the serial line """
    response: bytes = ser.readline()
    if not response:
        debug("No response from serial port.")
###        if line_count > conf.max_lines 
    line_count += 1
    return (response, line_count);

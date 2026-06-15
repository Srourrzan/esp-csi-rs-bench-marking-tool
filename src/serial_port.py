import queue
import threading
from time import sleep, time_ns
from serial import Serial
from serial.tools import list_ports

from debug import __FILE__, __LINE__;


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

def serial_producer(ser: Serial, raw_line_queue: queue.Queue, stop_event: threading.Event):
    """
    Dedicated worker thread that consumes hardware data as fast as the serial 
    buffer provides it, mitigating hardware buffer overflows.
    """
    while not stop_event.is_set():
        try:
            # Keep a small serial timeout so it checks the stop_event periodically
            response = ser.readline()
            if response:
                # Capture the host arrival time immediately on hardware read
                arrival_us = time_ns() // 1_000
                # Pack them together as a tuple before putting it intp the queue
                raw_line_queue.put((response, arrival_us))
        except Exception:
            break

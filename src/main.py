import queue
import threading
from time import time
from sys import exit, stderr
from logging import error, info#, debug;
from serial import Serial, SerialException

from parsing import Data
from config import Config
from utils import validate_sys
from debug import __FILE__, __LINE__
from workers.system_process import SysProcess
from parsing import EmptyLineError, Data
from serial_port import init_serial, SerialTimeoutError, serial_producer


def main() -> int:
    data: Data
    status: int
    conf: Config
    start = None

    status, conf = validate_sys()
    if (status < 0):
        return (1);
    if (conf.setup_logging() < -1):
        return (1);
    
    sys_procs = SysProcess(conf)
    data = Data(line_count = 0, header_parsed = False); 
    # sys_procs.init_processes(conf, data)
    thread_stop = threading.Event()

    try:
        with Serial(conf.usb_port, conf.baud_rate, timeout=conf.timeout) as ser:
            info(f"{__FILE__()}:{__LINE__()} Serial port {conf.usb_port} opened at {conf.baud_rate} baud.")
            init_serial(ser)
            # Initialize fst local thread queue
            raw_queue = queue.Queue(maxsize=conf.queue_config.max_queue_size)
            # Spin up the I/O concurrent producer thread
            sys_procs.producer_thread = threading.Thread(
                target=serial_producer,
                args=(ser, raw_queue, thread_stop),
                daemon=True
            )
            sys_procs.producer_thread.start()
            while (True):
                if start is not None and (time() - start >= conf.run_seconds):
                    info(f"{__FILE__()}:{__LINE__()} stopped after {conf.run_seconds} seconds")
                    break;
                try:
                    # 1. Unpack the packed response tuple from our I/O producer thread
                    raw_tuple = raw_queue.get(timeout=conf.queue_config.queue_timeout)
                    raw_response, host_us = raw_tuple  # host_us is now perfectly preserved!
                    data.decodeline(raw_response=raw_response)
                except queue.Empty:
                    continue
                except EmptyLineError:
                    continue
                if not data.header_parsed:
                    if data.parsed_tracking_rules(conf):
                        info(f"Firmware detected as: {data.firmware_type.name}. Initializing metrics processes...")
                        sys_procs.init_processes(conf, data)
                        continue
                else:
                    if not start:
                        start = time()
                    # lower_line = data.line.lower()
                    print(f"{__FILE__()}:{__LINE__()} line={data.line}")
                    # 1. Ask the data engine what kind of line we are dealing with
                    line_kind = data.get_line_kind()
                    # 2. Extract hardware time parameters (returns None safely for resource lines)
                    esp_ts = data.get_esp_ts() if line_kind == "metrics" else None
                    # Safety validation gate: if a metrics line failed to split a valid timestamp, drop it
                    if line_kind == "metrics" and esp_ts is None:
                        continue
                    # 3. Hand everything off to the process manager to handle routing dynamically!
                    sys_procs.route_payloads(
                        line_kind=line_kind,
                        raw_line=data.line,
                        host_us=host_us,
                        esp_ts=esp_ts
                    )

    except SerialTimeoutError as e:
        error(str(e))
        status = 3;
    except SerialException as e:
        print(f"{e}", file=stderr);
    except PermissionError:
        print("Permission denied - check user permissions", file=stderr);
        status = 1;
    except UnicodeDecodeError as e:
        print(f"error while decoding: {e}", file=stderr);
        status = 2;
    except KeyboardInterrupt:
        print("\nStopped by user.")
        status = 127;
    # except Exception as e:
    #     print(f"{__FILE__()}:{__LINE__()} Unexpected error: {e}", file=stderr);
    finally:
        # 1. Gracefully bring down the raw serial reader thread
        thread_stop.set()
        if sys_procs.producer_thread and sys_procs.producer_thread.is_alive():
            sys_procs.producer_thread.join(timeout=2.0)
        # 2. Extract our metadata string label safely
        fw_name = data.firmware_type.name if data.firmware_ded else "unknown"
        # 3. Dynamic dynamic multi-process cleanup execution
        sys_procs.shutdown_all(fw_name)
        if data.line_count == 0:
            info("No CSI data collected")
        info("Benchmark run completed.")
    return (status);

if __name__ == "__main__":
    status = main();
    exit(status);

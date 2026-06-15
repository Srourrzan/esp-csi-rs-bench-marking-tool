import queue
import threading
from sys import exit, stderr
from time import time, time_ns
from logging import error, info#, debug;
from serial import Serial, SerialException

from parsing import Data
from config import Config
from utils import validate_sys
from debug import __FILE__, __LINE__
from system_process import SysProcess
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
    
    sys_procs = SysProcess()
    data = Data(line_count = 0, header_parsed = False); 
    sys_procs.init_processes(conf, data)
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
                    # Non-blocking fetch from local producer queue
                    raw_response = raw_queue.get(timeout=conf.queue_config.queue_timeout)
                    host_ts = time_ns()
                    data.decodeline(raw_response=raw_response)
                except queue.Empty:
                    continue
                except EmptyLineError:
                    continue
                if not data.header_parsed:
                    if data.parsed_tracking_rules(conf):
                        continue
                else:
                    if not start:
                        start = time()
                    lower_line = data.line.lower()
                    print(f"{__FILE__()}:{__LINE__()} line={lower_line}")
                    # now we need to measure the avg heap usage
                    # We forward matching outputs down to our sub-prcess queue
                    if sys_procs.enabled_processes["resources"] and sys_procs.res_que is not None:
                        if "resmon:" in lower_line or "cpu:" in lower_line:
                            try:
                                sys_procs.res_que.put_nowait(data.line)
                            except queue.Full:
                                # drop if back-pressured; resource worker still computes summary
                                pass
                # else:
                    esp_ts = data.get_esp_ts()
                    if esp_ts is None:
                        continue
                    if sys_procs.enabled_processes["latency"] and sys_procs.lat_que is not None:
                        try:
                            sys_procs.lat_que.put_nowait((host_ts, esp_ts))
                        except queue.Full:
                            pass
                    if sys_procs.enabled_processes["throughput"] and sys_procs.tp_que is not None:
                        try:
                            # Send a low-overhead signal tag indicating a sample was processed
                            sys_procs.tp_que.put_nowait("TICK")
                        except queue.Full:
                            pass
                

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
        # if resources_enabled and res_proc is not None:
        #     res_stop.set()
        #     try:
        #         res_que.put_nowait(None)
        #     except Exception:
        #         pass
        #     res_proc.join(timeout=10)
        status = 127;
    # except Exception as e:
    #     print(f"{__FILE__()}:{__LINE__()} Unexpected error: {e}", file=stderr);
    finally:
        # 1. Gracefully bring down the raw serial reader thread
        thread_stop.set()
        if sys_procs.producer_thread and sys_procs.producer_thread.is_alive():
            sys_procs.producer_thread.join(timeout=2.0)
        # 2. Shutdown resource worker subprocess
        if sys_procs.enabled_processes.get("resources") and sys_procs.res_proc is not None:
            sys_procs.res_stop.set()
            try:
                sys_procs.res_que.put_nowait(None)
            except Exception:
                pass
            sys_procs.res_proc.join(timeout=5)
        # 3. Shutdown latency worker subprocess
        if sys_procs.enabled_processes.get("latency") and sys_procs.lat_proc is not None:
            sys_procs.lat_stop.set()
            try:
                sys_procs.lat_que.put_nowait(("SHUTDOWN", data.firmware_type.name))
            except Exception:
                pass
            sys_procs.lat_proc.join(timeout=5)
        # 4. Shutdown throughput worker subprocess cleanly
        if sys_procs.enabled_processes.get("throughput") and sys_procs.tp_proc is not None:
            sys_procs.tp_stop.set()
            try:
                fw_name = data.firmware_type.name if data.firmware_ded else "unknown"
                sys_procs.tp_que.put_nowait(("SHUTDOWN", fw_name))
            except Exception:
                pass
            sys_procs.tp_proc.join(timeout=5)
        if data.line_count == 0:
            info("No CSI data collected")
        info(f"Runtime log saved to: logs/runtime_{conf.run_ts}.log")
    return (status);

if __name__ == "__main__":
    status = main();
    exit(status);

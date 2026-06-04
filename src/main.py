import queue
import threading
from time import time
from typing import List
from sys import exit, stderr
from logging import error, info, debug;
from statistics import median, quantiles;
from serial import Serial, SerialException;
from multiprocessing import Queue, Event, Process

from stats import Stats;
from parsing import Data;
from config import Config;
from utils import validate_sys;
from debug import __FILE__, __LINE__;
from parsing import EmptyLineError, Data;
from serial_port import init_serial, SerialTimeoutError, serial_producer
from resources_worker import start_resources_process


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
    # Start resources worker if requested (accept str or list in future)
    run_seconds = getattr(conf, "run_seconds", 60) #run for 60 sec, add to config 
    resources_enabled = ((conf.task == "resources") or 
                         (isinstance(conf.task, list) and "resources" in conf.task))
    res_que: Queue = None
    res_stop: Event = None
    res_proc: Process = None
    if resources_enabled:
        res_que, res_stop, res_proc = start_resources_process(conf)
        print(f"resources worker is set")
    statis = None
    producer_thread = None
    thread_stop = threading.Event()

    try:
        statis = Stats(conf.csv_filename, conf.stats_filename)
        data = Data(line_count = 0, header_parsed = False);
        statis.setup_csv_files(conf)
        print(f"{__FILE__()}:{__LINE__()} statis csv files are set")
        with Serial(conf.usb_port, conf.baud_rate, timeout=conf.timeout) as ser:
            info(f"{__FILE__()}:{__LINE__()} Serial port {conf.usb_port} opened at {conf.baud_rate} baud.")
            init_serial(ser)

            # Initialize fst local thread queue
            raw_queue = queue.Queue(maxsize=50000)
            # Spin up the I/O concurrent producer thread
            producer_thread = threading.Thread(
                target=serial_producer,
                args=(ser, raw_queue, thread_stop),
                daemon=True
            )
            producer_thread.start()
            while (True):
                if start is not None and (time() - start >= run_seconds):
                    info(f"{__FILE__()}:{__LINE__()} stopped after {run_seconds} seconds")
                    break;
                try:
                    # Non-blocking fetch from local producer queue
                    raw_response = raw_queue.get(timeout=0.2)
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
                    # now we need to measure the avg heap usage
                    # We forward matching outputs down to our sub-prcess queue
                    if resources_enabled and res_que is not None:
                        try:
                            res_que.put_nowait(data.line)
                        except queue.Full:
                            # drop if back-pressured; resource worker still computes summary
                            pass
                        # TODO latency/throughput 

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
        if producer_thread and producer_thread.is_alive():
            producer_thread.join(timeout=2.0)
        # 2. Shutdown resource worker subprocess
        if resources_enabled and res_proc is not None:
            res_stop.set()
            try:
                res_que.put_nowait(None)
            except Exception:
                pass
            res_proc.join(timeout=5)
        if statis and statis.deltas:
            # if stats_file_handle:
            #     write_final_stats_csv(stats_csv_writer, deltas, BAUD_RATE, firmware_type)
            info(f"Collected {len(deltas)} samples.")
            info(f"Raw data CSV saved to: {conf.csv_filename}")
            info(f"Statistics CSV saved to: {conf.stats_filename}")
            statis.close();
        else:
            info("No CSI data collected")
        info(f"Runtime log saved to: logs/runtime_{conf.run_ts}.log")
    return (status);

if __name__ == "__main__":
    status = main();
    exit(status);

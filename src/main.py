import queue
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
from serial_port import init_serial, SerialTimeoutError
from resources_worker import start_resources_process


def main() -> int:
    data: Data;
    status: int;
    conf: Config;
    start = None;

    status, conf = validate_sys()
    if (status < 0):
        return (1);
    if (conf.setup_logging() < -1):
        return (1);
    # Start resources worker if requested (accept str or list in future)
    run_seconds = getattr(conf, "run_seconds", 60) #run for 60 sec, add to config 
    resources_enabled = ((conf.task == "resources") or 
                         (isinstance(conf.task, list) and "resources" in conf.task))
    res_que: Queue = None;
    res_stop: Event = None;
    res_proc: Process = None;
    print(f"is the resources process start before reading the data?")
    if resources_enabled:
        res_que, res_stop, res_proc = start_resources_process(conf)
        print(f"resources worker is set")
    statis = None;
    try:
        statis = Stats(conf.csv_filename, conf.stats_filename)
        data = Data(line_count = 0, header_parsed = False);
        statis.setup_csv_files(conf)
        print(f"statis csv files are set")
        with Serial(conf.usb_port, conf.baud_rate, timeout=conf.timeout) as ser:
            info(f"Serial port {conf.usb_port} opened at {conf.baud_rate} baud.")
            init_serial(ser)
            while (True):
                try:
                    if start is not None:
                        if time() - start >= run_seconds:
                            info(f"stopped after {run_seconds} seconds")
                            break;
                    line = data.getline(ser, conf)
                    if line is None:
                        continue;
                except EmptyLineError as e:
                    debug(str(e))
                    continue;
                if not data.header_parsed:
                    data.parse_header()
                    if data.header_parsed:
                        continue;
                if data.header_parsed:
                    data.detect_firmware_type(conf)
                    if not start:
                        start = time()
                    # now we need to measure the avg heap usage
                    if resources_enabled and res_que is not None:
                        try:
                            res_que.put_nowait(line)
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
        if resources_enabled and res_proc is not None:
            res_stop.set()
            try:
                res_que.put_nowait(None)
            except Exception:
                pass
            res_proc.join(timeout=10)
        status = 127;
    # except Exception as e:
    #     print(f"{__FILE__()}:{__LINE__()} Unexpected error: {e}", file=stderr);
    finally:
        if resources_enabled and res_proc is not None:
            res_stop.set()
            try:
                res_que.put_nowait(None)
            except Exception:
                pass
            res_proc.join(timeout=5)
        if statis and statis.deltas:
            if stats_file_handle:
                write_final_stats_csv(stats_csv_writer, deltas, BAUD_RATE, firmware_type)
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

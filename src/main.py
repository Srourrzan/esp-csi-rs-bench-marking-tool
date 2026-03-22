from typing import List
from sys import exit, stderr
from logging import error, info, debug;
from statistics import median, quantiles;
from serial import Serial, SerialException;

from stats import Stats;
from parsing import Data;
from config import Config;
from utils import validate_sys;
from debug import __FILE__, __LINE__;
from parsing import EmptyLineError, Data;
from serial_port import init_serial, SerialTimeoutError


def main() -> int:

    data: Data;
    status: int;
    conf: Config;

    status, conf = validate_sys()
    if (status < 0):
        return (1);
    if (conf.setup_logging() < -1):
        return (1);
    try:
        statis = Stats(conf.csv_filename, conf.stats_filename)
        data = Data(line_count = 0, header_parsed = False);
        statis.setup_csv_files(conf)
        with Serial(conf.usb_port, conf.baud_rate, timeout=conf.timeout) as ser:
            info(f"Serial port {conf.usb_port} opened at {conf.baud_rate} baud.")
            init_serial(ser)
            while (True):
                try:
                    line = data.getline(ser, conf)
                    if not line:
                        continue;
                    # if data.line_count == 100:
                    #     break
                except EmptyLineError as e:
                    debug(str(e))
                    continue;
                if not data.header_parsed:
                    data.parse_header()
                    if data.header_parsed:
                        continue;
                if data.header_parsed:
                    data.detect_firmware_type(conf)
                    # now we need to measure the avg heap usage

    except SerialTimeoutError as e: #move down
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
        exit(127);
    # except Exception as e:
    #     print(f"{__FILE__()}:{__LINE__()} Unexpected error: {e}", file=stderr);
    finally:
        if statis.deltas:
            if stats_file_handle:
                write_final_stats_csv(stats_csv_writer, deltas, BAUD_RATE, firmware_type)
            info(f"Collected {len(deltas)} samples.")
            info(f"Raw data CSV saved to: {conf.csv_filename}")
            info(f"Statistics CSV saved to: {conf.stats_filename}")
        else:
            info("No CSI data collected")
        info(f"Runtime log saved to: logs/runtime_{conf.run_ts}.log")
        statis.close();
    return (status);

if __name__ == "__main__":
    status = main();
    exit(status);

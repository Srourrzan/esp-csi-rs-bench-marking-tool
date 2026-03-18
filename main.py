#from csv import reader
from typing import List
from sys import exit, stderr
from statistics import median, quantiles;
from serial import Serial, SerialException;
from logging import error, info, debug;

from config import Config;
from debug import __FILE__, __LINE__;
from serial_port import init_serial, getline, SerialTimeoutError, EmptyLineError, find_header;
from utils import validate_sys;
from stats import Stats;

def main() -> int:

    status: int
    conf: Config
    firmware_type: str = "Unknown Firmware"
    header_parsed: bool = False
    line_count: int = 0;

    status, conf = validate_sys()
    if (status < 0):
        return (1);
    if (conf.setup_logging() < -1):
        return (1);
    try:
        statis = Stats()
        statis.setup_csv_files(conf)
        with Serial(conf.usb_port, conf.baud_rate, timeout=conf.timeout) as ser:
            info(f"Serial port {conf.usb_port} opened at {conf.baud_rate} baud.")
            init_serial(ser)
            while (True):
                try:
                    line, line_count = getline(ser, conf, line_count, header_parsed)
                    if not line:
                        continue;
                    if line_count == 100:
                        break
                except EmptyLineError as e:
                    debug(str(e))
                    continue;
                #header_parsed, col_index =
                header: List = find_header(line);
                # if line.startswith("type,"):
                #     header: List = next(reader([line]))
                #     col_index = {name: i for i, name in enumerate(header)}
                #     firmware_type, data_indc = detect_firmware_type(line)
                #     if "Unknown" not in firmware_type:
                #         header_parsed = True
                #     continue
                # if header_parsed and line.startswith(data_indc):
                #     try:
                #         fields: List = next(reader([line]))
                #         esp_epoch_us = int(fields[col_index["timestamp"]]) #here
                #         print(f"{__FILE__()}:{__LINE__()} timestamp={timestamp}")
                #     except (ValueError, IndexError, KeyError) as e:
                #         error(f"Parse error on CSI line: {e} | line: {line[:120]}")
                #         continue
                #     except Exception as e:
                #         error(f"Unexpected error parsing CSI line: {e} | line: {line[:120]}")
                #         continue
                #     if esp_epoch_us < 1_000_000_000:          # adjust threshold as needed
                #         debug(f"Skipping suspicious ESP timestamp {esp_epoch_us}")
                #         continue
                #     delta_us: int = host_rx_epoch_us - esp_epoch_us
                #     statis.deltas.append(delta_us)
                #     write_raw_delta(delta_csv_writer, host_rx_epoch_us, esp_epoch_us, delta_us)
                #     if len(deltas) % 500 == 0: #increase to 1000 or more, we have to consider the drift in clock 
                #         med = median(deltas)
                #         p90 = int(quantiles(statis.deltas, n=10)[8]) if len(deltas) >= 10 else "N/A"
                #         p99 = int(quantiles(statis.deltas, n=100)[98]) if len(deltas) >= 99 else "N/A"
                #         info(
                #             f"N={len(deltas):>6}  "
                #             f"median={med:>8.0f}μs  "
                #             f"p90={p90:>8}μs  "
                #             f"p99={p99:>8}μs  "
                #             f"last={delta_us:>8}μs"
                #         )
                #     if line_count > MAX_LINES_BEFORE_HEADER_TIMEOUT and not header_parsed and line.startswith(data_indc):
                #         logging.error("Received CSI data but header was not parsed within timeout. Possible issue with ESP data format or header transmission.")
                #         break
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
    except Exception as e:
        print(f"{__FILE__()}:{__LINE__()} Unexpected error: {e}", file=stderr);
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

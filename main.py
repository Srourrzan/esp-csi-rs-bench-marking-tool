from csv import reader
from os import makedirs
from sys import exit, stderr
from typing import List, Dict
from statistics import median, quantiles
from serial import Serial, SerialException
from logging import basicConfig, INFO, FileHandler, StreamHandler, error, info, debug

from serial_port import init_serial;
from utils import validate_sys, detect_firmware_type, now_epoch_us;
from logging_data import write_final_stats_csv, write_raw_delta, setup_csv_files
from config import LOG_DIR, CSV_DIR, TIMESTAMP, CSV_FILENAME, STATS_FILENAME, Config


# Ensure directories exist
makedirs(LOG_DIR, exist_ok=True)
makedirs(CSV_DIR, exist_ok=True)

basicConfig(
    level=INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        FileHandler(f"{LOG_DIR}/runtime_{TIMESTAMP}.log"), # Runtime logs to a separate file
        StreamHandler(stderr) # Console output for immediate feedback
    ]
)

def main() -> int:

        status: int
        conf: Config

        firmware_type: str = "Unknown Firmware"
        header_parsed: bool = False
        line_count: int = 0;
        MAX_LINES_BEFORE_HEADER_TIMEOUT: int = 500

        status, conf = validate_sys()
        if (status < 0):
                return(1);

        delta_file_handle, delta_csv_writer, stats_file_handle, stats_csv_writer = setup_csv_files()
        if not delta_file_handle:
                return (2);
        try:
                with Serial(usb_port, BAUD_RATE, timeout=10) as ser: #make timeout value part of json policy
                        info(f"Serial port {usb_port} opened at {BAUD_RATE} baud.")
                        info("Waiting for CSI data...")
                        init_serial(ser)
                        while (True):
                                response: bytes = ser.readline()
                                host_rx_epoch_us: int = now_epoch_us() #here
                                if not response:
                                        debug("No response from serial port.")
                                        if line_count > MAX_LINES_BEFORE_HEADER_TIMEOUT and not header_parsed:
                                                error("Timeout waiting for header. Is the ESP connected and sending data?")
                                                break
                                        continue
                                line_count += 1
                                try:
                                        line: str = response.decode("utf-8", errors="replace")
                                except Exception as e:
                                        error(f"Failed to decode response: {e} - raw: {response!r}")
                                        continue
                                line: str = line.strip()
                                if not line:
                                        debug("Received empty line.")
                                        continue
                                if line.startswith("type,"):
                                        header: List = next(reader([line]))
                                        col_index = {name: i for i, name in enumerate(header)}
                                        if "esp_epoch_us" not in col_index:
                                                print("ERROR: Header missing required field esp_epoch_us", file=stderr)
                                                return (10);
                                        firmware_type, data_indc = detect_firmware_type(line)
                                        if "Unknown" not in firmware_type:
                                                header_parsed = True
                                        continue
                                if header_parsed and line.startswith(data_indc):
                                        try:
                                                fields: List = next(reader([line]))
                                                esp_epoch_us = int(fields[col_index["esp_epoch_us"]]) #here
                                        except (ValueError, IndexError, KeyError) as e:
                                                error(f"Parse error on CSI line: {e} | line: {line[:120]}")
                                                continue
                                        except Exception as e:
                                                error(f"Unexpected error parsing CSI line: {e} | line: {line[:120]}")
                                                continue
                                        if esp_epoch_us < 1_000_000_000:          # adjust threshold as needed
                                                debug(f"Skipping suspicious ESP timestamp {esp_epoch_us}")
                                                continue
                                        delta_us: int = host_rx_epoch_us - esp_epoch_us
                                        deltas.append(delta_us)
                                        write_raw_delta(delta_csv_writer, host_rx_epoch_us, esp_epoch_us, delta_us)
                                        if len(deltas) % 500 == 0: #increase to 1000 or more, we have to consider the drift in clock 
                                                med = median(deltas)
                                                p90 = int(quantiles(deltas, n=10)[8]) if len(deltas) >= 10 else "N/A"
                                                p99 = int(quantiles(deltas, n=100)[98]) if len(deltas) >= 99 else "N/A"
                                                info(
                                                                f"N={len(deltas):>6}  "
                                                                f"median={med:>8.0f}μs  "
                                                                f"p90={p90:>8}μs  "
                                                                f"p99={p99:>8}μs  "
                                                                f"last={delta_us:>8}μs"
                                                )
                                        if line_count > MAX_LINES_BEFORE_HEADER_TIMEOUT and not header_parsed and line.startswith(data_indc):
                                                logging.error("Received CSI data but header was not parsed within timeout. Possible issue with ESP data format or header transmission.")
                                                break
        except SerialException as e:
                print(f"{e}", file=stderr);
        except PermissionError:
                print("Permission denied - check user permissions", file=stderr);
        except UnicodeDecodeError as e:
                print(f"error while decoding: {e}", file=stderr);
        except KeyboardInterrupt:
                print("\nStopped by user.")
                exit(127);
        except Exception as e:
                print(f"Unexpected error: {e}", file=stderr);
        finally:
                if delta_file_handle:
                        delta_file_handle.close()
                if stats_file_handle:
                        write_final_stats_csv(stats_csv_writer, deltas, BAUD_RATE, firmware_type)
                        stats_file_handle.close()
                if deltas:
                        info(f"Collected {len(deltas)} samples.")
                else:
                        info("No CSI data collected")
                info(f"Runtime log saved to: logs/runtime_{TIMESTAMP}.log")
                info(f"Raw data CSV saved to: {CSV_FILENAME}")
                info(f"Statistics CSV saved to: {STATS_FILENAME}")
        return (0);

if __name__ == "__main__":
        status = main();
        exit(status);

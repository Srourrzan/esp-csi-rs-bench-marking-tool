from csv import writer
from typing import List
from logging import error, info
from statistics import median, quantiles, stdev
from pydantic import BaseModel, PrivateAttr

from config import Config
from file_setup import FileSetup
from debug import __LINE__, __FILE__


class Stats(BaseModel):
    __delta: FileSetup = PrivateAttr();
    __stats: FileSetup = PrivateAttr();
    __deltas: list[int] = PrivateAttr();
    __median_val = PrivateAttr();
    __stdev_val = PrivateAttr();
    __min_val: int = PrivateAttr();
    __max_val: int = PrivateAttr();
    __p90_val = PrivateAttr();
    __p99_val = PrivateAttr();

    @property
    def deltas(self):
        return (self.__deltas);

    def __init(self, deltaname: str, statsname: str):
        try:
            self.__deltas = []
            self.__delta = FileSetup()
            self.__delta.init_file(deltaname)
            self.__stats = FileSetup()
            self.__stats.init_file(statsname)
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e
        return ;
    
    def close(self):
        """send a closing signal to the file's io"""
        if self.__delta:
            self.__delta.close_file()
        if self.__stats:
            self.__stats.close_file()
        return ;
    
    def setup_csv_files(self, conf: Config):
        """Sets up CSV writers for raw deltas and final statistics."""
        try:
            self.__init(conf.csv_filename, conf.stats_filename)
            self.__delta.write_row([
                'host_rx_epoch_us',
                'esp_epoch_us',
                'delta_us'
            ])
            self.__stats.write_row([
                "timestamp",
                "baud_rate",
                "firmware_type",
                "total_samples",
                "median_us",
                "stdev_us",
                "min_us",
                "max_us",
                "p90_us",
                "p99_us"
            ])
        except IOError as e:
            raise RuntimeError (
                f"{__FILE__()}:{__LINE__()} Failed to open CSV files: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError (
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e
        return ;

    def write_raw_delta(self, host_ts_us: int, esp_ts_us: int, delta: int):
        """Writes a single delta_us measurement to the raw data CSV."""
        try:
            if self.__delta.get_writer:
                self.__delta.write_row([host_ts_us, esp_ts_us, delta])
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e
        return ;

    def write_final_stats_csv(self, conf: Config, firmware_type: str):
        """Writes the final calculated statistics to the stats CSV."""
        if not self.__stats.get_writer or not self.__deltas:
            return ;
        self.__median_val = median(self.__deltas)
        self.__stdev_val = stdev(self.__deltas) if len (self.__deltas) > 1 else 0
        self.__min_val = min(self.__deltas)
        self.__max_val = max(self.__deltas)
        self.__p90_val = "N/A"
        self.__p99_val = "N/A"
        try:
            if len(self.__deltas) >= 10:
                q10 = quantiles(self.__deltas, n=10)
                self.__p90_val = int(q10[8]) if len(q10) > 8 else "N/A"
            elif len(self.__deltas) >= 99:
                q100 = quantiles(self.__deltas, n=100)
                self.__p99_val = int(q100[98]) if len(q100) > 98 else "N/A"
            self.__stats.write_row([
               conf.run_ts,
               conf.baud_rate,
               firmware_type,
               len(self.__deltas),
               f"{self.__median_val:.0f}",
               f"{self.__stdev_val:.0f}",
               self.__min_val,
               self.__max_val,
               self.__p90_val,
               self.__p99_val
            ])
            info("Final statistics written to CSV.")
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e
        return ;
        

    class Config:
        arbitrary_types_allowed = True;
    

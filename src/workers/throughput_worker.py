from os import path
from typing import Any
from time import time_ns
from dataclasses import dataclass

from parsing import Data
from config import Config
from workers.base_worker import BaseWorker
from metrics.throughput_stats import ThroughputStats

@dataclass
class ThroughputWorkerConf:
    run_ts: str
    baud_rate: int
    csv_dir: str
    firmware_name: str
    run_seconds: int = 0
    raw_prefix: str = "throughput_data_"
    stats_prefix: str = "throughput_stats_"
    queue_timeout: float = 0.1

class ThroughputWorker(BaseWorker[ThroughputWorkerConf, ThroughputStats]):
    ConfigClass = ThroughputWorkerConf

    def __init__(self):
        super().__init__(name="throughput_worker")
        self.current_window_count = 0
        self.last_window_flush = time_ns()

    def create_config(self, conf: Config, data: Data) -> ThroughputWorkerConf:
        target_dir = path.join(conf.csv_dir, data.firmware_type.name, "throughput")
        return ThroughputWorkerConf(
            run_ts=conf.run_ts,
            baud_rate=conf.baud_rate,
            csv_dir=target_dir,
            firmware_name=data.firmware_type.name,
            run_seconds=conf.run_seconds,
            queue_timeout=conf.queue_config.queue_timeout
        )

    def create_stats_tracker(self, w_conf: ThroughputWorkerConf) -> ThroughputStats:
        t_stats = ThroughputStats()
        t_stats.setup_files(w_conf.csv_dir, w_conf.run_ts, w_conf.raw_prefix, w_conf.stats_prefix)
        t_stats.setup_headers()
        return t_stats

    def process_message(self, msg: Any, stats: ThroughputStats, w_conf: ThroughputWorkerConf, ts_us: int) -> bool:
        if msg == "TICK":
            self.current_window_count += 1
        return True

    def process_periodic_window(self, stats: ThroughputStats, w_conf: ThroughputWorkerConf, now_ns: int) -> None:
        # Check if 1 second (1,000,000,000 nanoseconds) has passed to dump data
        if now_ns - self.last_window_flush >= 1_000_000_000:
            stats.record_window(now_ns // 1_000, self.current_window_count)
            self.current_window_count = 0
            self.last_window_flush = now_ns

def start_throughput_process(conf: Config, data: Data):
    return ThroughputWorker().start_process(conf, data)
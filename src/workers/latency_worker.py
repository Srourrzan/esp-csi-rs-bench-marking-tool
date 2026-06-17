from os import path
from typing import Any
from dataclasses import dataclass

from parsing import Data
from config import Config
from workers.base_worker import BaseWorker
from metrics.latency_stats import LatencyStats

@dataclass
class LatencyWorkerConf:
    run_ts: str
    baud_rate: int
    csv_dir: str
    firmware_name: str
    raw_prefix: str
    stats_prefix: str
    queue_timeout: float
    run_seconds: int = 0

class LatencyWorker(BaseWorker[LatencyWorkerConf, LatencyStats]):
    ConfigClass = LatencyWorkerConf  # Reference for the base class builder helper

    def __init__(self):
        super().__init__(name="latency_worker")

    def create_config(self, conf: Config, data: Data) -> LatencyWorkerConf:
        target_dir = path.join(conf.csv_dir, data.firmware_type.name, "latency")
        return LatencyWorkerConf(
            run_ts=conf.run_ts,
            baud_rate=conf.baud_rate,
            csv_dir=target_dir,
            firmware_name=data.firmware_type.name,
            raw_prefix=conf.csv_file_prefix,
            run_seconds=conf.run_seconds,
            stats_prefix=conf.stats_file_prefix,
            queue_timeout=conf.queue_config.queue_timeout
        )

    def create_stats_tracker(self, w_conf: LatencyWorkerConf) -> LatencyStats:
        l_stats = LatencyStats()
        l_stats.setup_files(w_conf.csv_dir, w_conf.run_ts, w_conf.raw_prefix, w_conf.stats_prefix)
        l_stats.setup_headers()
        return l_stats

    def process_message(self, msg: Any, stats: LatencyStats, w_conf: LatencyWorkerConf, ts_us: int) -> bool:
        if isinstance(msg, tuple) and len(msg) == 2:
            host_ts, esp_ts = msg
            stats.record_delta(host_ts, esp_ts)
        return True

# Export a clean factory function hook matching your importlib registry conventions
def start_latency_process(conf: Config, data: Data):
    return LatencyWorker().start_process(conf, data)
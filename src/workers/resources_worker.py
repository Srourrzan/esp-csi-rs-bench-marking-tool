from os import path
from typing import Any
from dataclasses import dataclass
from re import IGNORECASE, compile

from parsing import Data
from config import Config
from workers.base_worker import BaseWorker
from metrics.resources_stats import ResourcesStats

WI_FI = r"Wi[\-\u2010\u2011\u2012\u2013]?\s*Fi"
HEAP_RE = compile(
    rf"resmon:\s*Heap DRAM:\s*free=(\d+)\s*B?,\s*min_free_since_boot=(\d+)\s*B?,\s*largest_block=(\d+)\s*B?",
    IGNORECASE
)
STACK_RE = compile(
    rf"resmon:\s*{WI_FI}\s*task\s*stack\s*headroom:\s*(\d+)\s*B", 
    IGNORECASE
)
CPU_RE = compile(
    rf"cpu:\s*(?:{WI_FI}\s*task|CSI\s*task)\s*CPU\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*%", 
    IGNORECASE
)

@dataclass
class ResourcesWorkerConf:
    run_ts: str
    baud_rate: int
    csv_dir: str
    firmware_name: str
    run_seconds: int = 0
    raw_prefix: str = "resources_data_"
    stats_prefix: str = "resources_stats_"
    queue_timeout: float = 0.5

class ResourcesWorker(BaseWorker[ResourcesWorkerConf, ResourcesStats]):
    ConfigClass = ResourcesWorkerConf

    def __init__(self):
        super().__init__(name="resources_worker")

    def create_config(self, conf: Config, data: Data) -> ResourcesWorkerConf:
        target_dir = path.join(conf.csv_dir, data.firmware_type.name, "resources")
        return ResourcesWorkerConf(
            run_ts=conf.run_ts,
            baud_rate=conf.baud_rate,
            csv_dir=target_dir,
            firmware_name=data.firmware_type.name,
            run_seconds=conf.run_seconds,
            queue_timeout=conf.queue_config.queue_timeout
        )

    def create_stats_tracker(self, w_conf: ResourcesWorkerConf) -> ResourcesStats:
        r_stats = ResourcesStats()
        r_stats.setup_files(w_conf.csv_dir, w_conf.run_ts, w_conf.raw_prefix, w_conf.stats_prefix)
        r_stats.setup_headers()
        return r_stats

    def process_message(self, msg: Any, stats: ResourcesStats, w_conf: ResourcesWorkerConf, ts_us: int) -> bool:
        if isinstance(msg, str):
            if (m := HEAP_RE.search(msg)):
                free_b, min_free_b, largest_b = map(int, m.groups())
                stats.record_heap(ts_us, free_b, min_free_b, largest_b)
            elif (m := STACK_RE.search(msg)):
                headroom_b = int(m.group(1))
                stats.record_stack(ts_us, headroom_b)
            elif (m := CPU_RE.search(msg)):
                cpu_pct = float(m.group(1))
                stats.record_cpu(ts_us, cpu_pct)
        return True

def start_resources_process(conf: Config, data: Data):
    return ResourcesWorker().start_process(conf, data)
import queue
import signal
from dataclasses import dataclass, field
from statistics import median, quantiles, stdev
from multiprocessing import Process, Queue, Event

from config import Config
from parsing import Data
from base_stats import BaseStats
from debug import __FILE__, __LINE__


@dataclass
class LatencyWorkerConf:
    run_ts: str
    baud_rate: int
    csv_dir: str
    firmware_name: str
    raw_prefix: str
    stats_prefix: str
    queue_timeout: float


@dataclass
class LatencyStats(BaseStats):
    deltas: list[int] = field(default_factory=list)

    def setup_headers(self) -> None:
        self.raw.write_row(['host_time', 'esp_timestamp', 'delta_us'])
        self.stats.write_row([
            "timestamp", "baud_rate", "firmware_type", "total_samples",
            "median_us", "stdev_us", "min_us", "max_us", "p90_us", "p99_us"
        ])

    def record_delta(self, host_ts: int, esp_ts: int) -> None:
        delta_us = host_ts - esp_ts
        self.deltas.append(delta_us)
        self.raw.write_row([host_ts, esp_ts, delta_us])

    def finalize(self, run_ts: str, baud_rate: int, firmware_name: str) -> None:
        if not self.deltas:
            self.close_files()
            return
            
        med_val = median(self.deltas)
        std_val = stdev(self.deltas) if len(self.deltas) > 1 else 0
        min_val = min(self.deltas)
        max_val = max(self.deltas)
        p90_val = "N/A"
        p99_val = "N/A"
        
        if len(self.deltas) >= 10:
            q10 = quantiles(self.deltas, n=10)
            p90_val = int(q10[8]) if len(q10) > 8 else "N/A"
        if len(self.deltas) >= 99:
            q100 = quantiles(self.deltas, n=100)
            p99_val = int(q100[98]) if len(q100) > 98 else "N/A"
        self.stats.write_row([
            run_ts, baud_rate, firmware_name, len(self.deltas),
            f"{med_val:.0f}", f"{std_val:.0f}", 
            min_val, max_val, p90_val, p99_val
        ])
        
        self.close_files()


def __latency_worker_main(que: Queue, stop: Event, wdict: dict) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    w = LatencyWorkerConf(**wdict)
    l_stats = LatencyStats()
    
    l_stats.setup_files(w.csv_dir, w.run_ts, w.raw_prefix, w.stats_prefix)
    l_stats.setup_headers()
    try:
        print(f"{__FILE__()}:{__LINE__()}")
        while True:
            try:
                msg = que.get(timeout=w.queue_timeout)
            except queue.Empty:
                if stop.is_set():
                    break
                continue
            if msg is None:
                break
            if isinstance(msg, tuple) and len(msg) == 2:
                print(f"{__FILE__()}:{__LINE__()} msg: {msg}")
                if msg[0] == "SHUTDOWN":
                    w.firmware_name = msg[1]
                    break
                else:
                    host_ts, esp_ts = msg
                    l_stats.record_delta(host_ts, esp_ts)
    finally:
        l_stats.finalize(w.run_ts, w.baud_rate, w.firmware_name)

    
def start_latency_process(
    conf: Config,
    data: Data
) -> tuple[Queue, Event, Process]:
    wdict = dict(
        run_ts = conf.run_ts,
        baud_rate = conf.baud_rate,
        csv_dir = conf.csv_dir,
        firmware_name = data.firmware_type,
        raw_prefix=conf.csv_file_prefix,
        stats_prefix=conf.stats_file_prefix,
        queue_timeout=conf.queue_config.queue_timeout
    )
    que = Queue(maxsize=conf.queue_config.max_queue_size)
    stop = Event()
    proc = Process(
        target=__latency_worker_main,
        args=(que, stop, wdict),
        name="latency_worker",
        daemon=True
    )
    proc.start()

    return (que, stop, proc);

import time
import queue
import signal
from dataclasses import dataclass
from multiprocessing import Process, Queue, Event

from parsing import Data
from config import Config
from metrics.throughput_stats import ThroughputStats

@dataclass
class ThroughputWorkerConf:
    run_ts: str
    baud_rate: int
    csv_dir: str
    firmware_name: str
    raw_prefix: str = "throughput_data_"
    stats_prefix: str = "throughput_stats_"
    queue_timeout: float = 0.1

def __throughput_worker_main(que: Queue, stop: Event, wdict: dict) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    w = ThroughputWorkerConf(**wdict)
    t_stats = ThroughputStats()
    
    t_stats.setup_files(w.csv_dir, w.run_ts, w.raw_prefix, w.stats_prefix)
    t_stats.setup_headers()

    current_window_count = 0
    # Establish time benchmarks in nanoseconds for microsecond tracking accuracy
    last_window_flush = time.time_ns()

    try:
        while True:
            try:
                # Use a small timeout so we can dynamically check time windows even during quiet periods
                msg = que.get(timeout=w.queue_timeout)
            except queue.Empty:
                msg = None

            now_ns = time.time_ns()

            # Handle explicit pipeline closure tracking signals
            if msg is not None:
                if msg == "TICK":
                    current_window_count += 1
                elif isinstance(msg, tuple) and msg[0] == "SHUTDOWN":
                    w.firmware_name = msg[1]
                    # Flush any remaining counts left over before breaking
                    # if current_window_count > 0:
                    t_stats.record_window(now_ns // 1000, current_window_count)
                    break

            # If 1 second (1,000,000,000 nanoseconds) has passed, write out our current metrics count
            if now_ns - last_window_flush >= 1_000_000_000:
                t_stats.record_window(now_ns // 1000, current_window_count)
                current_window_count = 0
                last_window_flush = now_ns
                
            if msg is None and stop.is_set():
                if current_window_count > 0:
                    t_stats.record_window(now_ns // 1000, current_window_count)
                break
    finally:
        t_stats.finalize(w.run_ts, w.baud_rate, w.firmware_name)

def start_throughput_process(
        conf: Config,
        data: Data
    ) -> tuple[Queue, Event, Process]:
    wdict = dict(
        run_ts=conf.run_ts,
        baud_rate=conf.baud_rate,
        csv_dir=conf.csv_dir,
        firmware_name=data.firmware_type.name,
        queue_timeout=conf.queue_config.queue_timeout
    )
    que = Queue(maxsize=conf.queue_config.max_queue_size)
    stop = Event()
    proc = Process(
        target=__throughput_worker_main,
        args=(que, stop, wdict),
        name="throughput_worker",
        daemon=True
    )
    proc.start()
    return que, stop, proc
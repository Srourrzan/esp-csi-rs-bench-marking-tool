import time
import queue
import signal
from re import IGNORECASE, compile
from dataclasses import dataclass
from multiprocessing import Process, Queue, Event

from parsing import Data
from config import Config
from metrics.resources_stats import ResourcesStats

# Regular expression patterns for log parsing
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
    raw_prefix: str = "resources_data_"
    stats_prefix: str = "resources_stats_"
    queue_timeout: float = 0.5


def __resource_worker_main(que: Queue, stop: Event, wdict: dict) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    w = ResourcesWorkerConf(**wdict)
    r_stats = ResourcesStats()
    
    r_stats.setup_files(w.csv_dir, w.run_ts, w.raw_prefix, w.stats_prefix)
    r_stats.setup_headers()

    try:
        while True:
            try:
                msg = que.get(timeout=w.queue_timeout)
            except queue.Empty:
                if stop.is_set():
                    break
                continue

            if msg is None:
                break
                
            # Intercept unified shutdown broadcast tuple safely
            if isinstance(msg, tuple) and len(msg) == 2 and msg[0] == "SHUTDOWN":
                w.firmware_name = msg[1]
                break

            ts_us = time.time_ns() // 1_000
            
            if isinstance(msg, str):
                if (m := HEAP_RE.search(msg)):
                    free_b, min_free_b, largest_b = map(int, m.groups())
                    r_stats.record_heap(ts_us, free_b, min_free_b, largest_b)
                elif (m := STACK_RE.search(msg)):
                    headroom_b = int(m.group(1))
                    r_stats.record_stack(ts_us, headroom_b)
                elif (m := CPU_RE.search(msg)):
                    cpu_pct = float(m.group(1))
                    r_stats.record_cpu(ts_us, cpu_pct)
    finally:
        r_stats.finalize(w.run_ts, w.baud_rate, w.firmware_name)


def start_resources_process(
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
        target=__resource_worker_main, 
        args=(que, stop, wdict),
        name="resources_worker",
        daemon=True
    )
    proc.start()
    return (que, stop, proc)
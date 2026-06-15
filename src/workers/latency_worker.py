import queue
import signal
from dataclasses import dataclass
from multiprocessing import Process, Queue, Event

from parsing import Data
from config import Config
from debug import __FILE__, __LINE__
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
        firmware_name = data.firmware_type.name,
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

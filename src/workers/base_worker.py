import time
import queue
import signal
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from multiprocessing import Process, Queue, Event

from parsing import Data
from config import Config

ConfT = TypeVar('ConfT')
StatsT = TypeVar('StatsT')

class BaseWorker(ABC, Generic[ConfT, StatsT]):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def create_config(self, conf: Config, data: Data) -> ConfT:
        pass

    @abstractmethod
    def create_stats_tracker(self, w_conf: ConfT) -> StatsT:
        pass

    @abstractmethod
    def process_message(self, msg: Any, stats: StatsT, w_conf: ConfT, ts_us: int) -> bool:
        pass

    def process_periodic_window(self, stats: StatsT, w_conf: ConfT, now_ns: int) -> None:
        """Optional hook for workers requiring time-windowed flushes (like Throughput)."""
        pass

    def _worker_loop_entry(self, que: Queue, stop: Event, wdict: dict) -> None:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        
        w_conf = type(self).ConfigClass(**wdict) if hasattr(type(self), 'ConfigClass') else wdict
        stats = self.create_stats_tracker(w_conf)
        
        queue_timeout = getattr(w_conf, "queue_timeout", 0.5)
        baud_rate = getattr(w_conf, "baud_rate", 115200)
        run_ts = getattr(w_conf, "run_ts", "")

        try:
            while True:
                try:
                    msg = que.get(timeout=queue_timeout)
                except queue.Empty:
                    msg = None

                now_ns = time.time_ns()
                ts_us = now_ns // 1_000

                if msg is not None:
                    if msg is None:
                        break
                    if isinstance(msg, tuple) and len(msg) == 2 and msg[0] == "SHUTDOWN":
                        if hasattr(w_conf, 'firmware_name'):
                            w_conf.firmware_name = msg[1]
                        break

                    keep_running = self.process_message(msg, stats, w_conf, ts_us)
                    if not keep_running:
                        break

                # Fire periodic background execution frame hook transformations
                self.process_periodic_window(stats, w_conf, now_ns)

                if msg is None and stop.is_set():
                    break
        finally:
            fw_name = getattr(w_conf, "firmware_name", "unknown")
            run_seconds = getattr(w_conf, "run_seconds", 0)
            if hasattr(stats, "finalize"):
                stats.finalize(run_ts, baud_rate, fw_name, run_seconds)

    def start_process(self, conf: Config, data: Data) -> tuple[Queue, Event, Process]:
        w_conf = self.create_config(conf, data)
        wdict = w_conf.__dict__ if hasattr(w_conf, '__dict__') else w_conf
        
        que = Queue(maxsize=conf.queue_config.max_queue_size)
        stop = Event()
        proc = Process(
            target=self._worker_loop_entry,
            args=(que, stop, wdict),
            name=self.name,
            daemon=True
        )
        proc.start()
        return que, stop, proc
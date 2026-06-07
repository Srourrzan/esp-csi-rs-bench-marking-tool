from __future__ import annotations

import os
import time
import queue
import signal
from re import IGNORECASE, compile
from dataclasses import dataclass,field
from statistics import mean, median, quantiles
from multiprocessing import Process, Queue, Event
from typing import Optional

from file_setup import FileSetup
from config import Config

# Tolerant to ASCII hyphen, Unicode hyphen, en-dash, etc.
WI_FI = r"Wi[\-\u2010\u2011\u2012\u2013]?\s*Fi"
HEAP_RE = compile(
    rf"resmon:\s*Heap DRAM:\s*free=(\d+)\s*B?,\s*min_free_since_boot=(\d+)\s*B?,\s*largest_block=(\d+)\s*B?",
    IGNORECASE
)
STACK_RE = compile(
    rf"resmon:\s*{WI_FI}\s*task\s*stack\s*headroom:\s*(\d+)\s*B",
    IGNORECASE
)
# Accept either "Wi‑Fi task CPU" or "CSI task CPU"
CPU_RE = compile(
    rf"cpu:\s*(?:{WI_FI}\s*task|CSI\s*task)\s*CPU\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*%",
    IGNORECASE
)

@dataclass
class WorkerConf:
    run_ts: str
    baud_rate: int
    csv_dir: str
    raw_prefix: str = "resources_data_"
    stats_prefix: str = "resources_stats_"

@dataclass
class ResourcesStats:
    raw: FileSetup = field(default_factory=FileSetup)
    stats: FileSetup = field(default_factory=FileSetup)
    cpu_samples: list[float] = field(default_factory=list)
    heap_min_free_last: Optional[int] = None
    heap_min_free_first: Optional[int] = None
    heap_largest_block_min: Optional[int] = None
    stack_headroom_min: Optional[int] = None
    total_samples: int = 0;

    def setup_files(self, w: WorkerConf) -> None:
        os.makedirs(w.csv_dir, exist_ok=True)
        raw_path = os.path.join(w.csv_dir, f"{w.raw_prefix}{w.run_ts}.csv")
        stats_path = os.path.join(w.csv_dir, f"{w.stats_prefix}{w.run_ts}.csv")
        self.raw.init_file(raw_path)
        self.stats.init_file(stats_path)
        self.raw.write_row([
            "ts_us","kind","free_B",
            "min_free_since_boot_B","largest_block_B",
            "stack_headroom_B","cpu_percent"
            ])
        self.stats.write_row([
            "timestamp","baud_rate",
            "total_cpu_samples","cpu_mean_pct",
            "cpu_median_pct","cpu_p95_pct",
            "heap_min_free_start_B","heap_min_free_end_B",
            "heap_min_free_drop_B","largest_block_min_B",
            "stack_headroom_min_B"
        ])
        return ;

    def record_heap(self, ts_us: int, free_b: int, min_free_b: int, largest_b: int) -> None:
        self.total_samples += 1
        if self.heap_min_free_first is None:
            self.heap_min_free_first = min_free_b
        self.heap_min_free_last = min_free_b
        if self.heap_largest_block_min is None or largest_b < self.heap_largest_block_min:
            self.heap_largest_block_min = largest_b
        self.raw.write_row([ts_us, "heap", free_b, min_free_b, largest_b, "", ""])
        return ;

    def record_stack(self, ts_us: int, headroom_b: int) -> None:
        if self.stack_headroom_min is None or headroom_b < self.stack_headroom_min:
            self.stack_headroom_min = headroom_b
        self.raw.write_row([ts_us, "stack", "", "", "", headroom_b, ""])
        return ;

    def record_cpu(self, ts_us: int, cpu_pct: float) -> None:
        self.cpu_samples.append(cpu_pct)
        self.raw.write_row([ts_us, "cpu", "", "", "", "", f"{cpu_pct:.3f}"])
        return ;

    def finalize(self, w: WorkerConf) -> None:
        if self.cpu_samples:
            m = mean(self.cpu_samples)
            med = median(self.cpu_samples)
            p95 = quantiles(self.cpu_samples, n=100)[94] if len(self.cpu_samples) >= 2 else self.cpu_samples[0]
        else:
            m = med = p95 = 0.0

        drop = ""
        if self.heap_min_free_first is not None and self.heap_min_free_last is not None:
            drop = self.heap_min_free_first - self.heap_min_free_last
        self.stats.write_row([
            w.run_ts,
            w.baud_rate,
            len(self.cpu_samples),
            f"{m:.2f}",
            f"{med:.2f}",
            f"{p95:.2f}",
            self.heap_min_free_first if self.heap_min_free_first is not None else "",
            self.heap_min_free_last if self.heap_min_free_last is not None else "",
            drop,
            self.heap_largest_block_min if self.heap_largest_block_min is not None else "",
            self.stack_headroom_min if self.stack_headroom_min is not None else ""
        ])
        self.raw.close_file()
        self.stats.close_file()
        return ;

def __resource_worker_main(que: Queue, stop: Event, wdict: dict) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    w = WorkerConf(**wdict)
    rs = ResourcesStats()
    rs.setup_files(w)

    try:
        while True:
            try:
                _line = que.get(timeout=0.5)
                # print(f"resource worker line: {_line}")
            except queue.Empty:
                if stop.is_set():
                    break
                continue
            if _line is None:
                break
            ts_us = time.time_ns() // 1_000
            if (m := HEAP_RE.search(_line)):
                free_b, min_free_b, largest_b = map(int, m.groups())
                rs.record_heap(ts_us, free_b, min_free_b, largest_b)
            elif (m := STACK_RE.search(_line)):
                headroom_b = int(m.group(1))
                rs.record_stack(ts_us, headroom_b)
            elif (m := CPU_RE.search(_line)):
                cpu_pct = float(m.group(1))
                rs.record_cpu(ts_us, cpu_pct)
    finally:
        rs.finalize(w)
    return ;

def start_resources_process(conf: Config) -> tuple[Queue, Event, Process]:
    wdict = dict(
        run_ts=conf.run_ts, 
        baud_rate=conf.baud_rate, 
        csv_dir=conf.csv_dir
    )
    print(f"worker dict {wdict}")
    que = Queue(maxsize=10_000)
    stop = Event()
    proc = Process(
        target=__resource_worker_main, 
        args=(que, stop, wdict),
        name="resources_worker",
        daemon=True
    )
    proc.start()
    return (que, stop, proc);

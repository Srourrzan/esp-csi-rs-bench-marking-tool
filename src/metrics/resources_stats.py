from typing import Optional
from statistics import mean, median, quantiles
from dataclasses import dataclass, field

from metrics.base_stats import BaseStats


@dataclass
class ResourcesStats(BaseStats):
    cpu_samples: list[float] = field(default_factory=list)
    heap_min_free_last: Optional[int] = None
    heap_min_free_first: Optional[int] = None
    heap_largest_block_min: Optional[int] = None
    stack_headroom_min: Optional[int] = None
    total_samples: int = 0

    def setup_headers(self) -> None:
        self.raw.write_row([
            "ts_us", "kind", "free_B",
            "min_free_since_boot_B", "largest_block_B",
            "stack_headroom_B", "cpu_percent"
        ])
        self.stats.write_row([
            "timestamp", "baud_rate", "firmware_type",
            "total_cpu_samples", "cpu_mean_pct",
            "cpu_median_pct", "cpu_p95_pct",
            "heap_min_free_start_B", "heap_min_free_end_B",
            "heap_min_free_drop_B", "largest_block_min_B",
            "stack_headroom_min_B"
        ])

    def record_heap(self, ts_us: int, free_b: int, min_free_b: int, largest_b: int) -> None:
        self.total_samples += 1
        if self.heap_min_free_first is None:
            self.heap_min_free_first = min_free_b
        self.heap_min_free_last = min_free_b
        
        if self.heap_largest_block_min is None or largest_b < self.heap_largest_block_min:
            self.heap_largest_block_min = largest_b
            
        self.raw.write_row([ts_us, "heap", free_b, min_free_b, largest_b, "", ""])

    def record_stack(self, ts_us: int, headroom_b: int) -> None:
        if self.stack_headroom_min is None or headroom_b < self.stack_headroom_min:
            self.stack_headroom_min = headroom_b
        self.raw.write_row([ts_us, "stack", "", "", "", headroom_b, ""])

    def record_cpu(self, ts_us: int, cpu_pct: float) -> None:
        self.cpu_samples.append(cpu_pct)
        self.raw.write_row([ts_us, "cpu", "", "", "", "", f"{cpu_pct:.3f}"])

    def finalize(self, run_ts: str, baud_rate: int, firmware_name: str) -> None:
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
            run_ts,
            baud_rate,
            firmware_name,
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
        self.close_files()

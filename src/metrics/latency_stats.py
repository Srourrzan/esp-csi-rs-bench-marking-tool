from dataclasses import dataclass, field
from statistics import median, quantiles, stdev

from metrics.base_stats import BaseStats


@dataclass
class LatencyStats(BaseStats):
    deltas: list[int] = field(default_factory=list)

    def setup_headers(self) -> None:
        self.raw.write_row(['host_time', 'esp_timestamp', 'delta_us'])
        self.stats.write_row([
            "timestamp", "baud_rate", "firmware_type", 
            "run_seconds", "total_samples", "median_us", 
            "stdev_us", "min_us", "max_us", 
            "p90_us", "p99_us"
        ])

    def record_delta(self, host_ts: int, esp_ts: int) -> None:
        delta_us = host_ts - esp_ts
        self.deltas.append(delta_us)
        self.raw.write_row([host_ts, esp_ts, delta_us])

    def finalize(
            self, 
            run_ts: str, 
            baud_rate: int, 
            firmware_name: str, 
            run_seconds: int
        ) -> None:
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
            run_ts, baud_rate, firmware_name, run_seconds, len(self.deltas),
            f"{med_val:.0f}", f"{std_val:.0f}", 
            min_val, max_val, p90_val, p99_val
        ])
        
        self.close_files()
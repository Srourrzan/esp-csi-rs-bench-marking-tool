from statistics import mean, median
from dataclasses import dataclass, field

from metrics.base_stats import BaseStats


@dataclass
class ThroughputStats(BaseStats):
    # Tracks samples per window interval
    window_samples: list[int] = field(default_factory=list)

    def setup_headers(self) -> None:
        self.raw.write_row(['host_timestamp_us', 'samples_per_second'])
        self.stats.write_row([
            "timestamp", "baud_rate", "firmware_type", "total_runtime_sec",
            "mean_pps", "median_pps", "min_pps", "max_pps"
        ])

    def record_window(self, host_ts_us: int, sample_count: int) -> None:
        """Logs the total number of packets successfully read in the last window frame."""
        self.window_samples.append(sample_count)
        self.raw.write_row([host_ts_us, sample_count])

    def finalize(self, run_ts: str, baud_rate: int, firmware_name: str) -> None:
        if not self.window_samples:
            self.close_files()
            return
        
        mean_pps = mean(self.window_samples)
        med_pps = median(self.window_samples)
        min_pps = min(self.window_samples)
        max_pps = max(self.window_samples)
        self.stats.write_row([
            run_ts, baud_rate, firmware_name, len(self.window_samples),
            f"{mean_pps:.2f}", f"{med_pps:.2f}", min_pps, max_pps
        ])
        self.close_files()

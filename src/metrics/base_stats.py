import os
from dataclasses import dataclass, field
from file_setup import FileSetup

@dataclass
class BaseStats:
    raw: FileSetup = field(default_factory=FileSetup)
    stats: FileSetup = field(default_factory=FileSetup)

    def setup_files(
        self,
        csv_dir: str, 
        run_ts: str,
        raw_prefix: str,
        stats_prefix: str
    ) -> None:
        """Initializes raw and stats CSV files dynamically based on prefix types."""
        os.makedirs(csv_dir, exist_ok=True)
        raw_path = os.path.join(csv_dir, f"{raw_prefix}{run_ts}.csv")
        stats_path = os.path.join(csv_dir, f"{stats_prefix}{run_ts}.csv")

        self.raw.init_file(raw_path)
        self.stats.init_file(stats_path)

    def close_files(self) -> None:
        """Safely flushes and closes I/O streams."""
        if self.raw:
            self.raw.close_file()
        if self.stats:
            self.stats.close_file()


espressif csi repo `https://github.com/espressif/esp-csi`
espressif modified code for resource measurements repo `https://github.com/Srourrzan/espressif_csi_firmware/tree/master`



Naive latency (delta_us) is the raw, uncorrected difference between:

* The host’s timestamp when it receives the CSI data (host_rx_epoch_us).
* The ESP’s timestamp when it captured the CSI data (esp_epoch_us).


CSV Parsing Robustness

* Problem: Using reader([line]) repeatedly is error-prone. Use a single csv.reader instance.
* Fix:
```py
csv_reader = csv.reader([line])  # Reuse this once per line
fields = next(csv_reader)
```

We want synchronization to measure latency in the following manner:
The measure important here is Latency. As we discussed, we should measure the time from when CSI is captured until it is processed on a host. For that, probably looking at intervals between recieved messages and calculating a difference between the host clock and the ESP clock would be the most accurate. Additionally, the throughput is important, meaning how much data we can push through while maintaining minimum latency?

#### The current latency measurement is:
```py
delta_us = host_rx_epoch_us - esp_epoch_us
```
-> esp_epoch_us → ESP’s SNTP‑aligned timestamp.
-> host_rx_epoch_us → Host’s NTP‑aligned timestamp.
-> Since both reference UTC,
Δ ≈ (serial transmission + waiting + residual offset).


Next Steps for Deeper Analysis

1. 
Plot delta_us Over Time
To check for drift or sudden jumps.

2. 
Compare Across Firmwares
Run your script with different ESP32 firmwares and compare the latency distributions.


## HEAP and CPU Usage:

 I should fix the below summarization to be more accurate and actionable:

* CPU% (Wi‑Fi task):
This is the percent of total CPU time the Wi‑Fi driver task got during the last ~1 s window (your code uses uxTaskGetSystemState before/after a 1 s delay). CSI packets arrive in bursts and your callback prints a lot, so the Wi‑Fi task’s CPU usage spikes and dips. That’s normal. To compare firmwares, don’t use a single instant—sample for 30–60 s and report mean/median and a high percentile (e.g., p95). ESP‑IDF’s run‑time stats use an ESP‑TIMER counter (1 MHz), so the percentage is time‑based and stable across CPU freq changes. On dual‑core chips, the printed percent is relative to total time across all cores (so a task using one core fully can read ~50%). (docs.espressif.com docs.espressif.com)
* Heap free / largest block:
heap_caps_get_free_size and heap_caps_get_largest_free_block are live snapshots. They’ll bounce as the Wi‑Fi driver allocates buffers on the fly. That’s expected. They’re still useful for spotting fragmentation or runaway growth over long runs. (docs.espressif.com)
* Min free since boot:
heap_caps_get_minimum_free_size is the lowest value seen since power‑on. It’s the most comparable number across builds—if it’s stable after a long test, you haven’t leaked RAM. (docs.espressif.com)
* Stack headroom (uxTaskGetStackHighWaterMark):
Returns bytes on ESP‑IDF (not words). It’s the smallest amount of free stack that task ever had. After your workload has “peaked,” this stabilizes and is a good safety indicator. (docs.espressif.com)

How to get “accurate” (comparable) numbers

* CPU: Collect many 1‑s samples over 30–60 s of steady traffic; report mean, median, and p95. Avoid using a single instant. (docs.espressif.com)
* RAM: Use min_free_since_boot and largest_block after a long run. Track whether min_free_since_boot decreases over hours; if it does, you have a leak. (docs.espressif.com)
* Stack: Let the system run through its worst‑case traffic; then log the headroom once it stabilizes. Smaller = closer to overflow. (docs.espressif.com)


## The Architecture Strategy

Instead of executing everything inline within a blocking loop, we will decouple the architecture:

- Producer (Thread): A lightweight background thread whose exclusive job is to pull lines out of serial.readline() as fast as possible and append them into a fast, in-memory queue.Queue.

- Main Engine / Coordinator (Main Thread): Pulls raw strings out of the local queue, feeds them through the regex cleaning and firmware matching logic, and passes off the specialized lines to downstream components.

- Resources Worker (Separate Process): It continues running on its own CPU core, picking up performance-monitoring string matches forwarded from the engine.


## Installation & Usage

This project uses a standard `pyproject.toml` file to manage its configuration and dependencies. 

### Setting up the Environment

You can install this project directly into your Conda environment. This will automatically install dependencies like `pyserial` and `json5` using the `pip` provided by Conda, keeping them correctly isolated to your environment.

1. Activate your Conda virtual environment:
   ```bash
   conda activate <your-environment-name>
   ```

2. Install the project in "editable mode" (`-e`). This means any changes you make to the source code will take effect immediately without needing to reinstall:
   ```bash
   pip install -e .
   ```

### Running the Tool

Installing the project via `pyproject.toml` automatically creates an entry point script.
Instead of having to run `python src/main.py`, you can now run the tool from anywhere using:

```bash
esp-csi-bench
```

*(Note: Your environment must be active for this command to be available.)*

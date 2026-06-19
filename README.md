## Installation & Usage

This project uses a standard `pyproject.toml` file to manage its configuration and dependencies. 

### Setting up the Environment

You can install this project directly into your Conda environment. This will automatically install dependencies like `pyserial` and `json5` using the `pip` provided by Conda, keeping them correctly isolated to your environment.

1. Activate your Conda virtual environment:
   ```bash
   conda activate <your-environment-name>
   ```

2. Install the project dependencies:
   ```bash
   pip install .
   ```

### Running the Tool

You can run the tool directly using Python:

```bash
python src/main.py
```

*(Note: Your environment must be active for this command to be available.)*


## The Architecture Strategy

Instead of executing everything inline within a blocking loop, we will decouple the architecture:

- Producer (Thread): A lightweight background thread whose exclusive job is to pull lines out of serial.readline() as fast as possible and append them into a fast, in-memory queue.Queue.

- Main Engine / Coordinator (Main Thread): Pulls raw strings out of the local queue, feeds them through the regex cleaning and firmware matching logic, and passes off the specialized lines to downstream components.

- Resources Worker (Separate Process): It continues running on its own CPU core, picking up performance-monitoring string matches forwarded from the engine.

### Throughput strategy 

Because processing throughput on a single-line basis is highly inefficient, the correct pattern is Time-Windowed Aggregation:

- The Main Thread (main.py) flags every time a valid CSI data line is successfully parsed. It will push a timestamped notification token down to a dedicated Throughput Process.

- The Throughput Worker keeps a rolling counter. Every time 1 second passes, it flushes that count to a raw data log (e.g., 450 samples/sec) and calculates rolling performance stats.


## Measurements and Analysis

Naive latency (delta_us) is the raw, uncorrected difference between:

* The host’s timestamp when it receives the CSI data (host_rx_epoch_us).
* The ESP’s timestamp when it captured the CSI data (esp_epoch_us).


#### The current latency measurement is:
```py
delta_us = host_rx_epoch_us - esp_epoch_us
```


Next Steps for Deeper Analysis

1. 
Plot delta_us Over Time
To check for drift or sudden jumps.

2. 
Compare Across Firmwares
Run script with different ESP32 firmwares and compare the latency distributions.


## HEAP and CPU Usage:

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


## Flash Size
- espressif firmware:
```
Total sizes:
Used static DRAM:   28880 bytes ( 151856 remain, 16.0% used)
      .data size:   12944 bytes
      .bss  size:   15936 bytes
Used static IRAM:   85790 bytes (  45282 remain, 65.5% used)
      .text size:   84763 bytes
   .vectors size:    1027 bytes
Used Flash size :  551303 bytes
      .text     :  459811 bytes
      .rodata   :   91236 bytes
Total image size:  650037 bytes (.bin may be padded larger)
```

- Hernandez firmware:
```
Total sizes:
Used static DRAM:   33932 bytes ( 146804 remain, 18.8% used)
      .data size:   13444 bytes
      .bss  size:   20488 bytes
Used static IRAM:   86242 bytes (  44830 remain, 65.8% used)
      .text size:   85215 bytes
   .vectors size:    1027 bytes
Used Flash size :  769711 bytes
      .text     :  610183 bytes
      .rodata   :  159272 bytes
Total image size:  869397 bytes (.bin may be padded larger)
```

- Wi-ESP firmware:
```
Total sizes:
Used static DRAM:   28788 bytes ( 151948 remain, 15.9% used)
      .data size:   13284 bytes
      .bss  size:   15504 bytes
Used static IRAM:   86326 bytes (  44746 remain, 65.9% used)
      .text size:   85299 bytes
   .vectors size:    1027 bytes
Used Flash size :  553119 bytes
      .text     :  462907 bytes
      .rodata   :   89956 bytes
Total image size:  652729 bytes (.bin may be padded larger)
```


## Additional Notes

CSV Parsing Robustness

* Problem: Using reader([line]) repeatedly is error-prone. Use a single csv.reader instance.
* Fix:
```py
csv_reader = csv.reader([line])  # Reuse this once per line
fields = next(csv_reader)
```


The following repositories are relevant to this project:
espressif csi repo `https://github.com/espressif/esp-csi`
espressif modified code for resource measurements repo `https://github.com/Srourrzan/espressif_csi_firmware/tree/master`

Hernandez forked and fixed code `https://github.com/Srourrzan/ESP32-CSI-Tool-Hernandez `
Hernandez modified code for resource measurements repo `https://github.com/Srourrzan/ESP32-CSI-Tool-Hernandez/tree/usage_resources`

Wi-ESP forked and fixed code `https://github.com/Srourrzan/Wi-ESP_benchmark`

monitoring utils repo: `https://github.com/Srourrzan/esp32-monitoring-utils`

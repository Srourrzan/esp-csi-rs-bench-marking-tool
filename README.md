
espressif csi repo `https://github.com/espressif/esp-csi`
espressif modified code for resource measurements repo `https://github.com/Srourrzan/espressif_csi_firmware/tree/master`



Naive latency (delta_us) is the raw, uncorrected difference between:

* The host’s timestamp when it receives the CSI data (host_rx_epoch_us).
* The ESP’s timestamp when it captured the CSI data (esp_epoch_us).

It does NOT account for:

* Clock drift/jitter (SNTP isn’t perfect; clocks can drift by ±ms).
* Serialization delays (time to send data over UART/USB).
* Host-side buffering (OS/kernel delays in reading serial data).

Host Clock Synchronization //FIXED

* Problem: now_epoch_us() uses time.time_ns(), which depends on the host OS’s NTP sync. If the host isn’t synced to the same NTP server as the ESP, delta_us will be systematically biased.
* Fix: Ensure the host is synced to the same NTP server (e.g., pool.ntp.org) via timedatectl (Linux) or w32tm (Windows).

If you wanted to tighten synchronization below a millisecond (purely academic curiosity):

* Run a local NTP daemon (chronyd) pointing to the same NTP pool the ESP uses (pool.ntp.org).
* Configure SNTP update interval on the ESP to 10–30 seconds (esp_sntp_set_sync_interval()).

That can narrow host–ESP offset to < 2 ms.

Serialization Delay Exclusion

* Problem: delta_us includes the time to serialize CSI data over UART/USB (e.g., 10–20 ms at 921600 baud). This isn’t “processing latency” but “transport latency.”
* Fix: If you want only ESP processing latency, use GPIO synchronization (toggle a pin in wifi_csi_rx_cb and measure the time between toggle and host detection).

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

from dataclasses import dataclass
from multiprocessing import Queue as mpQueue, Event as mpEvent, Process

# @dataclass
# class WorkerProcess:
#     que: mpQueue = None



@dataclass
class SysProcess:
    producer_thread = None
    res_que: mpQueue = None
    res_stop: mpEvent = None
    res_proc: Process = None
    lat_que: mpQueue = None
    lat_stop: mpEvent = None
    lat_proc: Process = None
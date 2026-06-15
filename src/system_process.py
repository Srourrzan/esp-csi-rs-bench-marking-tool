from dataclasses import dataclass, field
from multiprocessing import Queue as mpQueue, Event as mpEvent, Process

from parsing import Data
from config import Config
from workers.latency_worker import start_latency_process
from workers.resources_worker import start_resources_process
from workers.throughput_worker import start_throughput_process

# @dataclass
# class WorkerProcess:
#     que: mpQueue = None

#configure

@dataclass
class Proc:
    que: mpQueue = None
    proc: Process = None
    que: mpQueue = None

@dataclass
class SysProcess:
    producer_thread = None
    res_que: mpQueue = None
    res_stop: mpEvent = None
    res_proc: Process = None
    lat_que: mpQueue = None
    lat_stop: mpEvent = None
    lat_proc: Process = None
    tp_que: mpQueue = None
    tp_stop: mpEvent = None
    tp_proc: Process = None
    enabled_processes: dict = field(default_factory=dict)

    def init_processes(self, conf: Config, data: Data):
        task_conf = conf.task
        task_list = [task_conf] if isinstance(task_conf, str) else task_conf
        self.enabled_processes["resources"] = True if "resources" in task_list else False
        self.enabled_processes["latency"] = True if "latency" in task_list else False
        self.enabled_processes["throughput"] = True if "throughput" in task_list else False

        if self.enabled_processes["resources"]:
            self.res_que, self.res_stop, self.res_proc = start_resources_process(conf)
        if self.enabled_processes["latency"]:
            self.lat_que, self.lat_stop, self.lat_proc = start_latency_process(conf, data)
        if self.enabled_processes["throughput"]:
            self.tp_que, self.tp_stop, self.tp_proc = start_throughput_process(conf, data)

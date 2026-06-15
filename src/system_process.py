import queue
import importlib
from sys import stderr
from typing import Dict, List, Callable
from dataclasses import dataclass, field
from multiprocessing import Queue as mpQueue, Event as mpEvent, Process

from parsing import Data
from config import Config
# from workers.latency_worker import start_latency_process
# from workers.resources_worker import start_resources_process
# from workers.throughput_worker import start_throughput_process


@dataclass
class ActiveTask:
    """Encapsulates the runtime synchronization primitives for a running sub-worker."""
    que: mpQueue
    stop: mpEvent
    proc: Process

class SysProcess:
    def __init__(self, conf: Config):
        self.producer_thread = None
        # Track only what is actively running
        self.active_tasks: Dict[str, ActiveTask] = {}
        # Define a clean mapping configuration of supported engines
        self._WORKER_REGISTRY: Dict[str, Callable] = {}
        self._discover_and_build_registry(conf)

    def _discover_and_build_registry(self, conf: Config):
        """
        Dynamically imports worker modules from disk at runtime based strictly 
        on the strings provided in the config file's 'valid_tasks' list.
        """
        for task_name in conf.valid_tasks:
            try:
                # 1. Dynamically construct the file path name string on the fly
                # e.g., "latency" -> module name "workers.latency_worker"
                module_name = f"workers.{task_name}_worker"
                
                # 2. Programmatically import the module file from your filesystem
                worker_module = importlib.import_module(module_name)
                
                # 3. Look up the factory function dynamically inside that imported module file
                # e.g., expects a function named "start_latency_process" inside latency_worker.py
                function_name = f"start_{task_name}_process"
                start_factory = getattr(worker_module, function_name)
                
                # 4. If found, register it as an authorized system capability
                self._WORKER_REGISTRY[task_name] = start_factory
                
            except ModuleNotFoundError:
                print(f"Configuration Error: Handled task string '{task_name}' listed in 'valid_tasks' "
                      f"but no matching file found at 'src/workers/{task_name}_worker.py'.", file=stderr)
            except AttributeError:
                print(f"Architecture Error: Module 'src/workers/{task_name}_worker.py' exists, "
                      f"but it is missing the expected factory function '{function_name}'.", file=stderr)


    def init_processes(self, conf: Config, data: Data):
        """Dynamically spins up only the pipelines specified in the configuration files."""
        task_conf = conf.task
        requested_tasks = [task_conf] if isinstance(task_conf, str) else task_conf

        for task_name in requested_tasks:
            if task_name not in self._WORKER_REGISTRY:
                raise ValueError(
                    f"Task request parameter '{task_name}' is unauthorixed by your 'valid_tasks' configuration files rules"
                    )
            # Execute the dynamically discovered file hook directly
            start_factory = self._WORKER_REGISTRY[task_name]
            que, stop, proc = start_factory(conf, data)
            self.active_tasks[task_name] = ActiveTask(que=que, stop=stop, proc=proc)

    def send_to_task(self, task_name: str, payload):
        """Safely delivers metrics payloads down active pipelines."""
        if task_name in self.active_tasks:
            try:
                self.active_tasks[task_name].que.put_nowait(payload)
            except queue.Full:
                pass

    def shutdown_all(self, firmware_name: str):
        """Gracefully targets and cleans up active runtime tasks."""
        for task in self.active_tasks.values():
            task.stop.set()

        for _, task in self.active_tasks.items():
            try:
                task.que.put_nowait(("SHUTDOWN", firmware_name))
            except Exception:
                pass

        for task in self.active_tasks.values():
            if task.proc and task.proc.is_alive():
                task.proc.join(timeout=3.0)

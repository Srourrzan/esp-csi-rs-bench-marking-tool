from typing import Dict
from dataclasses import dataclass

@dataclass
class QueueConfig:
    max_queue_size: int = 0
    queue_timeout: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, int|float]) -> 'QueueConfig':
        return (cls(**data))

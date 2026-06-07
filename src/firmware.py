from typing import Dict
from dataclasses import dataclass

@dataclass
class Firmware:
    name: str = ""
    timestamp_label: str = ""
    data_header: bool = True
    delimater: str = ":"

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Firmware':
        return (cls(**data));


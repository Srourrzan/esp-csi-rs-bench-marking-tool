from typing import Dict
from dataclasses import dataclass

from debug import __FILE__, __LINE__

@dataclass
class Firmware:
    name: str = "";
    timestamp_label: str = "";
    data_header: bool = True;

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Firmware':
        return (cls(**data));


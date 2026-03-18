from dataclasses import dataclass, field
from typing import Dict

from debug import __FILE__, __LINE__

@dataclass
class Firmware:
    name: str;
    timestamp_label: str;

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Firmware':
        return (cls(**data));


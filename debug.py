from inspect import currentframe, getframeinfo
from pydantic import dataclass

@dataclass
class Debug:
    filename: str;
    line: int;

def get_linenumber(cf) -> int:
    return (cf.f_back.f_lineno);


def get_file_name(cf) -> str:
    filename = getframeinfo(cf).filename
    return (filename);


def init_debug(cf):
    Debug()

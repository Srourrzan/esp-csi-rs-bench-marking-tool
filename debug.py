from inspect import currentframe, getframeinfo
from pydantic.dataclasses import dataclass
from os.path import basename

@dataclass
class Debug:
    filename: str;
    line: int;

def __LINE__() -> int:
    cf = currentframe()
    return (cf.f_back.f_lineno);


def __FILE__() -> str:
    cf = currentframe()
    # filename = getframeinfo(cf).filename
    filename = cf.f_back.f_code.co_filename
    filename = basename(filename)
    return (filename);


# def init_debug(cf):
#     Debug()

from csv import writer
from typing import List
from io import TextIOWrapper
from dataclasses import dataclass, field

from debug import __LINE__, __FILE__

@dataclass
class FileSetup:
    __writer: writer = field(init=False);
    __io: TextIOWrapper = field(init=False);

    @property
    def get_writer(self):
        if not self.__writer:
            raise AttributeError(
                f"{__FILE__()}:{__LINE__()} 'FileSetup' object has no attribute '_FileSetup__writer'"
            )
        return (self.__writer);

    def init_file(self, filename: str):
        try:
            self.__io = open(filename, 'w', newline='', encoding='utf-8')
            self.__writer = writer(self.__io)
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e
        return ;

    def write_row(self, row: List):
        """Write a header to the associated CSV file"""
        try:
            self.__writer.writerow(row)
        except Exception as e:
            raise RuntimeError(
                f"{__FILE__()}:{__LINE__()} Encountered an error from {e}"
            ) from e
        return ;

    def close_file(self):
        """Close the associated file"""
        if self.__io:
            self.__io.close()
        return ;


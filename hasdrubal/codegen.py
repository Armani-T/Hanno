from collections import namedtuple
from enum import Enum, unique

Instruction = namedtuple("Instruction", ("code", "args"))


@unique
class ByteCodes(Enum):
    EXIT = 0
    LOAD_NAME = 1
    LOAD_INT = 2
    LOAD_STR = 3
    LOAD_FLOAT = 4
    LOAD_BOOL = 5
    LOAD_FUNC = 6

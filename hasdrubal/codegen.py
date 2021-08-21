from collections import namedtuple
from enum import Enum, unique

Instruction = namedtuple("Instruction", ("opcode", "operands"))


@unique
class OpCodes(Enum):
    EXIT = 0
    LOAD_NAME = 1
    LOAD_INT = 2
    LOAD_STR = 3
    LOAD_FLOAT = 4
    LOAD_BOOL = 5
    LOAD_FUNC = 6

    BUILD_TUPLE = 7
    BUILD_LIST = 8

    CALL = 11

    STORE = 12

    BRANCH = 13
    BRANCH_FALSE = 14

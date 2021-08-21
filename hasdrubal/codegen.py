from collections import namedtuple
from enum import Enum, unique

Instruction = namedtuple("Instruction", ("opcode", "operands"))


@unique
class OpCodes(Enum):
    EXIT = 0

    LOAD_VAL = 1
    LOAD_VAR = 2

    BUILD_TUPLE = 3
    BUILD_LIST = 4

    CALL = 5

    STORE_VAR = 6

    BRANCH = 7
    BRANCH_FALSE = 8

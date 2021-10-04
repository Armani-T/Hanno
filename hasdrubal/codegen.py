from decimal import Decimal
from enum import Enum, unique
from functools import reduce
from operator import add, methodcaller
from typing import NamedTuple, Optional, Sequence, Tuple, Union

from asts import base, visitor
from scope import Scope

Operands = Union[
    Tuple[int],
    Tuple[Sequence["Instruction"]],
    Tuple[int, int],
    Tuple[bool],
    Tuple[float],
    Tuple[str],
    Tuple[()],
]

BYTE_ORDER = "big"
STRING_ENCODING = "UTF-8"


@unique
class OpCodes(Enum):
    """The numbers that identify different instructions."""

    LOAD_BOOL = 1
    LOAD_FLOAT = 2
    LOAD_INT = 3
    LOAD_STRING = 4

    BUILD_FUNC = 5
    BUILD_TUPLE = 6
    BUILD_LIST = 7

    CALL = 8

    LOAD_VAR = 9
    STORE_VAR = 10

    SKIP = 11
    SKIP_FALSE = 12


Instruction = NamedTuple("Instruction", (("opcode", OpCodes), ("operands", Operands)))


class InstructionGenerator(visitor.BaseASTVisitor[Sequence[Instruction]]):
    """
    Turn the AST into a linear stream of bytecode instructions.

    Attributes
    ----------
    current_index: int
        The number given to the next unique name found in a scope.
    prev_indexes: list[int]
        A stack containing the value of `current_index` for the
        enclosing scopes.
    current_scope: Scope[int]
        A data structure containing the names defined in this lexical
        scope. This particular scope maps each name to a unique integer
        index.
    function_level: int
        How deep inside nested function the visitor currently is. If
        it's `0`, then the visitor is not inside any function.
    """

    def __init__(self) -> None:
        self.current_index: int = 0
        self.prev_indexes: list[int] = []
        self.current_scope: Scope[int] = Scope(None)
        self.function_level: int = 0

    def _push_scope(self) -> None:
        self.current_scope = Scope(self.current_scope)
        self.prev_indexes.append(self.current_index)
        self.current_index = 0

    def _pop_scope(self) -> None:
        self.current_scope = self.current_scope.parent
        self.current_index = self.prev_indexes.pop()

    def visit_block(self, node: base.Block) -> Sequence[Instruction]:
        self._push_scope()
        result = reduce(add, map(methodcaller("visit", self), node.body()), ())
        self._pop_scope()
        return result

    def visit_cond(self, node: base.Cond) -> Sequence[Instruction]:
        cons_body = node.cons.visit(self)
        else_body = node.else_.visit(self)
        return (
            *node.pred.visit(self),
            Instruction(OpCodes.SKIP_FALSE, (len(cons_body),)),
            *cons_body,
            Instruction(OpCodes.SKIP, (len(else_body),)),
            *else_body,
        )

    def visit_define(self, node: base.Define) -> Sequence[Instruction]:
        value = node.value.visit(self)
        if node.target not in self.current_scope:
            self.current_scope[node.target] = self.current_index
            self.current_index += 1
        return (
            *value,
            Instruction(OpCodes.STORE_VAR, (self.current_scope[node.target],)),
        )

    def visit_func_call(self, node: base.FuncCall) -> Sequence[Instruction]:
        return (
            *node.callee.visit(self),
            *node.caller.visit(self),
            Instruction(OpCodes.CALL, ()),
        )

    def visit_function(self, node: base.Function) -> Sequence[Instruction]:
        self._push_scope()
        self.function_level += 1
        self.current_index = 1
        self.current_scope[node.param] = 0
        func_body = node.body.visit(self)
        self.function_level -= 1
        self._pop_scope()
        return (Instruction(OpCodes.BUILD_FUNC, (func_body)),)

    def visit_name(self, node: base.Name) -> Sequence[Instruction]:
        if node not in self.current_scope:
            self.current_scope[node] = self.current_index
            self.current_index += 1

        depth = self.current_scope.depth(node)
        depth = 0 if self.function_level and depth else (depth + 1)
        index = self.current_scope[node]
        return (Instruction(OpCodes.LOAD_VAR, (depth, index)),)

    def visit_scalar(self, node: base.Scalar) -> Sequence[Instruction]:
        opcode: OpCodes = {
            bool: OpCodes.LOAD_BOOL,
            float: OpCodes.LOAD_FLOAT,
            int: OpCodes.LOAD_INT,
            str: OpCodes.LOAD_STRING,
        }[type(node.value)]
        return (Instruction(opcode, (node.value,)),)

    def visit_type(self, node) -> Sequence[Instruction]:
        return ()

    def visit_vector(self, node: base.Vector) -> Sequence[Instruction]:
        elements = tuple(node.elements)
        elem_instructions = reduce(add, map(methodcaller("visit", self), elements), ())
        opcode: OpCodes = (
            OpCodes.BUILD_TUPLE
            if node.vec_type == base.VectorTypes.TUPLE
            else OpCodes.BUILD_LIST
        )
        return (
            *elem_instructions,
            Instruction(opcode, (len(elements),)),
        )


def encode_instructions(
    stream: Sequence[Instruction],
    func_pool: Optional[list[bytes]] = None,
    string_pool: Optional[list[bytes]] = None,
) -> bytearray:
    """
    Encode the bytecode instruction objects given as a stream of bytes
    that can be written to a file or kept in memory.

    Parameters
    ----------
    stream: Sequence[Instruction]
        The bytecode instruction objects to be converted.
    func_pool: Optional[list[bytes]] = None
        Where the bytecode for function objects is stored before being
        added to the byte stream. If you are calling this function in
        a non-recursive way, then don't pass in this argument.
    string_pool: Optional[list[bytes]] = None
        Where encoded UTF-8 string objects are stored before being
        added to the byte stream. If you are calling this function in
        a non-recursive way, then don't pass in this argument.

    Returns
    -------
    bytearray
        The resulting stream of bytes.
    """
    func_pool = [] if func_pool is None else func_pool
    string_pool = [] if string_pool is None else string_pool
    result_stream = bytearray(len(stream) * 8)
    for index, instruction in enumerate(stream):
        end_index = index + 8
        result_stream[index:end_index] = encode(
            instruction.opcode,
            instruction.operands,
            func_pool,
            string_pool,
        )
    return result_stream


def encode(
    opcode: OpCodes,
    operands: Operands,
    func_pool: list[bytes],
    string_pool: list[bytes],
) -> bytes:
    """
    Encode a single bytecode instruction in a bytearray. The
    bytearray is guaranteed to have a length of 8.

    Parameters
    ----------
    opcode: OpCodes
        The specific type of operation that should be performed.
    operands: Operands
        The values that will be used in the operation to be performed.
    func_pool: list[bytes]
        Where the bytecode for function objects is stored before being
        added to the byte stream.
    string_pool: list[bytes]
        Where encoded UTF-8 string objects are stored before being
        added to the byte stream.

    Returns
    -------
    bytes
        The resulting bytes.
    """
    operand_space: bytes
    if opcode == OpCodes.CALL:
        operand_space = b""
    elif opcode == OpCodes.LOAD_STRING:
        string_pool.append(operands[0].encode(STRING_ENCODING))
        pool_index = len(string_pool) - 1
        operand_space = pool_index.to_bytes(4, BYTE_ORDER)
    elif opcode == OpCodes.BUILD_FUNC:
        func_pool.append(encode_instructions(operands[0], func_pool, string_pool))
        pool_index = len(func_pool) - 1
        operand_space = pool_index.to_bytes(4, BYTE_ORDER)
    elif opcode == OpCodes.LOAD_BOOL:
        operand_space = _encode_load_bool(operands[0])
    elif opcode == OpCodes.LOAD_FLOAT:
        operand_space = _encode_load_float(operands[0])
    elif opcode == OpCodes.LOAD_VAR:
        operand_space = _encode_load_var(*operands)
    else:
        operand_space = operands[0].to_bytes(4, BYTE_ORDER)

    return opcode.value.to_bytes(1, BYTE_ORDER) + operand_space.ljust(7, b"\x00")


def _encode_load_bool(value: bool) -> bytes:
    int_value = 255 if value else 0
    return int_value.to_bytes(1, BYTE_ORDER)


def _encode_load_float(value: float) -> bytes:
    sign, digits, exponent = Decimal(value).as_tuple()
    digits = abs(digits)
    return (
        (b"\xff" if sign else b"\x00")
        + digits.to_bytes(3, BYTE_ORDER)
        + exponent.to_bytes(3, BYTE_ORDER)
    )


def _encode_load_var(depth: int, index: int) -> bytes:
    # NOTE: I had to add a null byte at the end because the return
    #  value must have a length of 7.
    return depth.to_bytes(2, BYTE_ORDER) + index.to_bytes(4, BYTE_ORDER)

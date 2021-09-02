from collections import namedtuple
from decimal import Decimal
from enum import Enum, unique
from functools import reduce
from operator import add, methodcaller
from typing import Optional, Sequence

from asts.base import VectorTypes
from asts.types import Type, TypeApply
from scope import Scope
from visitor import NodeVisitor
from asts import typed

BYTE_ORDER = "big"
STRING_ENCODING = "UTF-8"

Instruction = namedtuple("Instruction", ("opcode", "operands"))


@unique
class OpCodes(Enum):
    """The numbers that identify different instructions."""

    EXIT = 0

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


class InstructionGenerator(NodeVisitor[Sequence[Instruction]]):
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

    def run(self, node: typed.TypedASTNode) -> Sequence[Instruction]:
        return (
            *node.visit(self),
            Instruction(OpCodes.EXIT, ()),
        )

    def visit_block(self, node: typed.Block) -> Sequence[Instruction]:
        self._push_scope()
        result = reduce(add, map(methodcaller("visit", self), node.body()), ())
        self._pop_scope()
        return result

    def visit_cond(self, node: typed.Cond) -> Sequence[Instruction]:
        cons_body = node.cons.visit(self)
        else_body = node.else_.visit(self)
        return (
            *node.pred.visit(self),
            Instruction(OpCodes.SKIP_FALSE, (len(cons_body),)),
            *cons_body,
            Instruction(OpCodes.SKIP, (len(else_body),)),
            *else_body,
        )

    def visit_define(self, node: typed.Define) -> Sequence[Instruction]:
        if node.body is not None:
            new_node = typed.FuncCall(
                node.span,
                node.type_,
                typed.Function(
                    node.span,
                    TypeApply.func(
                        node.span,
                        node.target.type_,
                        node.body.type_,
                    ),
                    node.target,
                    node.body,
                ),
                node.value,
            )
            return new_node.visit(self)

        value = node.value.visit(self)
        if node.target not in self.current_scope:
            self.current_scope[node.target] = self.current_index
            self.current_index += 1

        return (
            *value,
            Instruction(OpCodes.STORE_VAR, (self.current_scope[node.target],)),
        )

    def visit_func_call(self, node: typed.FuncCall) -> Sequence[Instruction]:
        return (
            *node.callee.visit(self),
            *node.caller.visit(self),
            Instruction(OpCodes.CALL, ()),
        )

    def visit_function(self, node: typed.Function) -> Sequence[Instruction]:
        self._push_scope()
        self.function_level += 1
        self.current_index = 1
        self.current_scope[node.param] = 0
        func_body = node.body.visit(self)
        self.function_level -= 1
        self._pop_scope()
        return (Instruction(OpCodes.BUILD_FUNC, (func_body)),)

    def visit_name(self, node: typed.Scalar) -> Sequence[Instruction]:
        if node not in self.current_scope:
            self.current_scope[node] = self.current_index
            self.current_index += 1

        depth = self.current_scope.depth(node)
        depth = 0 if self.function_level and depth else (depth + 1)
        index = self.current_scope[node]
        return (Instruction(OpCodes.LOAD_VAR, (depth, index)),)

    def visit_scalar(self, node: typed.Scalar) -> Sequence[Instruction]:
        opcode = {
            bool: OpCodes.LOAD_BOOL,
            float: OpCodes.LOAD_FLOAT,
            int: OpCodes.LOAD_INT,
            str: OpCodes.LOAD_STRING,
        }[type(node.value)]
        return (Instruction(opcode, (node.value,)),)

    def visit_type(self, node: Type) -> Sequence[Instruction]:
        return ()

    def visit_vector(self, node: typed.Vector) -> Sequence[Instruction]:
        elements = tuple(node.elements)
        elem_instructions = reduce(add, map(methodcaller("visit", self), elements), ())
        op_code = (
            OpCodes.BUILD_TUPLE
            if node.vec_type == VectorTypes.TUPLE
            else OpCodes.BUILD_LIST
        )
        return (
            *elem_instructions,
            Instruction(op_code, (len(elements),)),
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
    stream: Iterator[Instruction]
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
    bytes
        The resulting stream of bytes.
    """
    func_pool: list[bytes] = [] if func_pool is None else func_pool
    string_pool: list[bytes] = [] if string_pool is None else string_pool
    result_stream = bytearray(len(stream) * 8)
    for index, instruction in enumerate(stream):
        end = index + 8
        result_stream[index:end] = encode(instruction, func_pool, string_pool)
    return result_stream


def encode(
    instruction: Instruction,
    func_pool: list[bytes],
    string_pool: list[bytes],
) -> bytearray:
    """
    Encode a single bytecode instruction in a bytearray. The
    bytearray is guaranteed to have a length of 8.

    Parameters
    ----------
    instruction: Instruction
        The bytecode instruction object to be converted.
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
    code = bytearray(8)
    opcode, operands = instruction
    code[0] = opcode.value

    if opcode == OpCodes.LOAD_STRING:
        actual = operands[0].encode(STRING_ENCODING)
        string_pool.append(actual)
        pool_index = len(string_pool) - 1
        code[1:] = pool_index.to_bytes(7, BYTE_ORDER)
        return code
    if opcode == OpCodes.BUILD_FUNC:
        func_bytes = encode_instructions(operands[0], func_pool, string_pool)
        func_pool.append(func_bytes)
        pool_index = len(func_pool) - 1
        code[1:] = pool_index.to_bytes(7, BYTE_ORDER)
        return code

    func = {
        OpCodes.LOAD_BOOL: _encode_load_bool,
        OpCodes.LOAD_FLOAT: _encode_load_float,
        OpCodes.LOAD_VAR: _encode_load_var,
    }.get(opcode, _encode_int_value)
    code[1:] = func(*operands)
    return code


def _encode_load_bool(value: bool) -> bytes:
    int_value = 255 if value else 0
    return int_value.to_bytes(7, "little")


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
    return depth.to_bytes(2, BYTE_ORDER) + index.to_bytes(4, BYTE_ORDER) + b"\x00"


def _encode_int_value(value: int) -> bytes:
    return value.to_bytes(4, BYTE_ORDER).ljust(7, b"\x00")

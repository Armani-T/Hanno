from decimal import Decimal
from enum import Enum, unique
from functools import reduce
from itertools import chain
from operator import add, methodcaller
from typing import Any, Iterator, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from asts.base import VectorTypes
from asts import lowered, visitor
from scope import Scope

BYTE_ORDER = "big"
LIBRARY_MODE = False
STRING_ENCODING = "UTF-8"
NATIVE_OP_CODES: Mapping[lowered.OperationTypes, int] = {
    lowered.OperationTypes.ADD: 1,
    lowered.OperationTypes.DIV: 2,
    lowered.OperationTypes.EQUAL: 3,
    lowered.OperationTypes.EXP: 4,
    lowered.OperationTypes.GREATER: 5,
    lowered.OperationTypes.JOIN: 6,
    lowered.OperationTypes.LESS: 7,
    lowered.OperationTypes.MUL: 8,
    lowered.OperationTypes.NEG: 9,
    lowered.OperationTypes.SUB: 10,
}


@unique
class OpCodes(Enum):
    """The numbers that identify different instructions."""

    LOAD_BOOL = 1
    LOAD_FLOAT = 2
    LOAD_INT = 3
    LOAD_STRING = 4

    LOAD_FUNC = 5
    BUILD_LIST = 6
    BUILD_TUPLE = 7

    LOAD_NAME = 8
    STORE_NAME = 9

    CALL = 10
    DO_OP = 11

    JUMP = 12
    JUMP_FALSE = 13


Instruction = NamedTuple("Instruction", (("opcode", OpCodes), ("operands", Any)))


class InstructionGenerator(visitor.LoweredASTVisitor[Sequence[Instruction]]):
    """
    Turn the AST into a linear stream of bytecode instructions.

    Attributes
    ----------
    current_index: int
        The number given to the next unique name found in a scope.
    prev_indexes: Sequence[int]
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
        self.prev_indexes: List[int] = []
        self.current_scope: Scope[int] = Scope(None)
        self.function_level: int = 0

    def _push_scope(self) -> None:
        self.current_scope = Scope(self.current_scope)
        self.prev_indexes.append(self.current_index)
        self.current_index = 0

    def _pop_scope(self) -> None:
        self.current_scope = self.current_scope.up()
        self.current_index = self.prev_indexes.pop()

    def visit_block(self, node: lowered.Block) -> Sequence[Instruction]:
        self._push_scope()
        result = reduce(add, (expr.visit(self) for expr in node.body), ())
        self._pop_scope()
        return result

    def visit_cond(self, node: lowered.Cond) -> Sequence[Instruction]:
        cons_body = node.cons.visit(self)
        else_body = node.else_.visit(self)
        return (
            *node.pred.visit(self),
            Instruction(OpCodes.JUMP_FALSE, (len(cons_body),)),
            *cons_body,
            Instruction(OpCodes.JUMP, (len(else_body),)),
            *else_body,
        )

    def visit_define(self, node: lowered.Define) -> Sequence[Instruction]:
        value = node.value.visit(self)
        if node.target not in self.current_scope:
            self.current_scope[node.target] = self.current_index
            self.current_index += 1
        return (
            *value,
            Instruction(OpCodes.STORE_NAME, (self.current_scope[node.target],)),
        )

    def visit_func_call(self, node: lowered.FuncCall) -> Sequence[Instruction]:
        arg_stack = tuple(chain(map(methodcaller("visit", self), reversed(node.args))))
        return (
            *arg_stack,
            *node.func.visit(self),
            Instruction(OpCodes.CALL, (len(arg_stack),)),
        )

    def visit_function(self, node: lowered.Function) -> Sequence[Instruction]:
        self._push_scope()
        self.function_level += 1
        self.current_index = 1
        for param in node.params:
            self.current_scope[param] = self.current_index
            self.current_index += 1

        func_body = node.body.visit(self)
        self.function_level -= 1
        self._pop_scope()
        return (Instruction(OpCodes.LOAD_FUNC, (func_body,)),)

    def visit_name(self, node: lowered.Name) -> Sequence[Instruction]:
        if node not in self.current_scope:
            self.current_scope[node] = self.current_index
            self.current_index += 1

        depth = self.current_scope.depth(node)
        depth = 0 if self.function_level and depth else (depth + 1)
        index = self.current_scope[node]
        return (Instruction(OpCodes.LOAD_NAME, (depth, index)),)

    def visit_native_operation(
        self, node: lowered.NativeOperation
    ) -> Sequence[Instruction]:
        right = () if node.right is None else node.right.visit(self)
        left = node.left.visit(self)
        operator_number = NATIVE_OP_CODES[node.operation]
        return (
            *right,
            *left,
            Instruction(OpCodes.DO_OP, (operator_number,)),
        )

    def visit_scalar(self, node: lowered.Scalar) -> Sequence[Instruction]:
        opcode: OpCodes = {
            bool: OpCodes.LOAD_BOOL,
            float: OpCodes.LOAD_FLOAT,
            int: OpCodes.LOAD_INT,
            str: OpCodes.LOAD_STRING,
        }[type(node.value)]
        return (Instruction(opcode, (node.value,)),)

    def visit_vector(self, node: lowered.Vector) -> Sequence[Instruction]:
        elements = tuple(node.elements)
        elem_instructions = reduce(add, map(methodcaller("visit", self), elements), ())
        opcode: OpCodes = (
            OpCodes.BUILD_TUPLE
            if node.vec_type == VectorTypes.TUPLE
            else OpCodes.BUILD_LIST
        )
        return (
            *elem_instructions,
            Instruction(opcode, (len(elements),)),
        )


def to_bytecode(ast: lowered.LoweredASTNode) -> bytes:
    """
    Convert the high-level AST into a stream of bytes which can be
    written to a file or kept in memory.

    Parameters
    ----------
    ast: lowered.LoweredASTNode
        The high-level AST.

    Returns
    -------
    bytes
        The resulting stream of bytes that represent the bytecode
        instruction objects.
    """
    generator = InstructionGenerator()
    instruction_objects = generator.run(ast)
    stream, funcs, strings = encode_instructions(instruction_objects, [], [])
    funcs = encode_func_pool(funcs)
    strings = encode_string_pool(strings)
    header = generate_header(stream, len(funcs), len(strings), LIBRARY_MODE, "utf-8")
    return encode_all(header, stream, funcs, strings, LIBRARY_MODE)


def encode_func_pool(func_pool: List[bytes]) -> bytes:
    body = b";".join(
        [
            b"%b%b" % (len(func).to_bytes(2, BYTE_ORDER), func)
            for func in func_pool
        ]
    )
    return body + b";"


def encode_string_pool(string_pool: List[bytes]) -> bytes:
    body = b";".join(
        [
            b"%b%b" % (len(string).to_bytes(2, BYTE_ORDER), string)
            for string in string_pool
        ]
    )
    return body + b";"


def generate_header(
    stream: bytes,
    func_pool_size: int,
    string_pool_size: int,
    lib_mode: bool,
    encoding_used: str,
) -> bytes:
    """
    Create the header data for the bytecode file.

    Parameters
    ----------
    stream: bytes
        The actual stream of bytecode instructions.
    func_pool_size: int
        The size of the function pool.
    string_pool_size: int
        The size of the string pool.
    lib_mode: bool
        Whether or not the
    encoding_used: str

    Returns
    -------
    bytes
        The header data for the bytecode file.
    """
    return b"M:%b;F:%b;S:%b;E:%b;%b" % (
        b"\01" if lib_mode else b"\00",
        func_pool_size.to_bytes(4, BYTE_ORDER),
        string_pool_size.to_bytes(4, BYTE_ORDER),
        encoding_used.encode("ASCII").ljust(16, b"\x00"),
        b"" if lib_mode else (b"C:%d;" % len(stream).to_bytes(4, BYTE_ORDER)),
    )


def encode_all(
    header: bytes, stream: bytes, funcs: bytes, strings: bytes, lib_mode: bool
) -> bytes:
    """
    Combine the various parts of the bytecode into a single byte string.

    Parameters
    ----------
    header: bytes
        The bytecode's header data.
    stream: bytes
        The actual bytecode instructions.
    funcs: bytes
        The function pool.
    strings: bytes
        The string pool.
    lib_mode: bool
        Whether to build a library bytecode file or an application one.

    Returns
    -------
    bytes
        The full bytecode file as it should be passed to the VM.
    """
    if lib_mode:
        return b"".join((header, b"\r\n\r\n\r\n", strings, b"\r\n\r\n", funcs))
    return b"".join(
        (header, b"\r\n\r\n\r\n", strings, b"\r\n\r\n", funcs, b"\r\n\r\n", stream)
    )


def encode_instructions(
    stream: Sequence[Instruction],
    func_pool: List[bytes],
    string_pool: List[bytes],
) -> Tuple[bytearray, List[bytes], List[bytes]]:
    """
    Encode the bytecode instruction objects given as a stream of bytes
    that can be written to a file or kept in memory.

    Parameters
    ----------
    stream: Sequence[Instruction]
        The bytecode instruction objects to be converted.
    func_pool: List[bytes]
        Where the bytecode for function objects is stored before being
        added to the byte stream.
    string_pool: List[bytes]
        Where encoded UTF-8 string objects are stored before being
        added to the byte stream.

    Returns
    -------
    bytearray
        The resulting stream of bytes.
    """
    result_stream = bytearray(len(stream) * 8)
    for index, instruction in enumerate(stream):
        start = index * 8
        end = start + 8
        result_stream[start:end] = encode(
            instruction.opcode,
            instruction.operands,
            func_pool,
            string_pool,
        )
    return result_stream, func_pool, string_pool


def encode(
    opcode: OpCodes,
    operands: Any,
    func_pool: List[bytes],
    string_pool: List[bytes],
) -> bytes:
    """
    Encode a single bytecode instruction in a bytearray. The
    bytearray is guaranteed to have a length of 8.

    Parameters
    ----------
    opcode: OpCodes
        The specific type of operation that should be performed.
    operands: Any
        The values that will be used in the operation to be performed.
    func_pool: List[bytes]
        Where the bytecode for function objects is stored before being
        added to the byte stream.
    string_pool: List[bytes]
        Where encoded UTF-8 string objects are stored before being
        added to the byte stream.

    Returns
    -------
    bytes
        The resulting bytes.
    """
    operand_space: bytes
    if opcode == OpCodes.CALL:
        operand_space = operands[0].to_bytes(1, BYTE_ORDER)
    elif opcode == OpCodes.LOAD_STRING:
        string_pool.append(operands[0].encode(STRING_ENCODING))
        pool_index = len(string_pool) - 1
        operand_space = pool_index.to_bytes(4, BYTE_ORDER)
    elif opcode == OpCodes.LOAD_FUNC:
        func_pool.append(encode_instructions(operands[0], func_pool, string_pool))
        pool_index = len(func_pool) - 1
        operand_space = pool_index.to_bytes(4, BYTE_ORDER)
    elif opcode == OpCodes.LOAD_BOOL:
        operand_space = b"\xff" if operands[0] else b"\x00"
    elif opcode == OpCodes.LOAD_FLOAT:
        operand_space = _encode_load_float(operands[0])
    elif opcode == OpCodes.LOAD_NAME:
        operand_space = _encode_load_var(*operands)
    else:
        operand_space = operands[0].to_bytes(4, BYTE_ORDER)
    return opcode.value.to_bytes(1, BYTE_ORDER) + operand_space.ljust(7, b"\x00")


def _encode_load_float(value: float) -> bytes:
    data = Decimal(value).as_tuple()
    digits = sum(
        [(n * (10 ** (len(data.digits) - i))) for i, n in enumerate(data.digits)]
    )
    return (
        (b"\xff" if data.sign else b"\x00")
        + digits.to_bytes(3, BYTE_ORDER)
        + data.exponent.to_bytes(3, BYTE_ORDER)
    )


def _encode_load_var(depth: int, index: int) -> bytes:
    # NOTE: I had to add a null byte at the end because the return
    #  value must have a length of 7.
    return depth.to_bytes(2, BYTE_ORDER) + index.to_bytes(4, BYTE_ORDER)


def compress(original: bytes) -> bytes:
    """
    Shrink down the bytecode using a simple run-length encoding.

    Parameters
    ----------
    original: bytes
        The original bytecode stream as it was produced by the bytecode
        generator.

    Returns
    -------
    bytes
        The compresses version of `original`. If the compression for
        whatever reason returns a string longer than `original` then
        this function will just return `original` unchanged.
    """
    compressed_version = _to_byte_stream(_encode_bytecode(original))
    if len(compressed_version) >= len(original):
        return original
    return compressed_version


def _encode_bytecode(source: bytes) -> Iterator[Tuple[int, bytes]]:
    if not source:
        return

    amount = 1
    prev_char: Optional[int] = None
    char = -1
    for char in source:
        if char == prev_char:
            amount += 1
        else:
            if prev_char is not None:
                yield (amount, prev_char.to_bytes(1, BYTE_ORDER))
            amount = 1
            prev_char = char

    if char != -1:
        yield (amount, char.to_bytes(1, BYTE_ORDER))


def _normalise(stream: Iterator[Tuple[int, bytes]]) -> Iterator[Tuple[int, bytes]]:
    for amount, char in stream:
        while amount > 0xFF:
            yield (0xFF, char)
            amount -= 0xFF
        yield (amount, char)


def _to_byte_stream(stream: Iterator[Tuple[int, bytes]]) -> bytes:
    return b"".join(
        amount.to_bytes(1, BYTE_ORDER) + char for amount, char in _normalise(stream)
    )

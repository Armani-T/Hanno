from codecs import lookup
from decimal import Decimal
from enum import Enum, unique
from functools import reduce
from operator import add, methodcaller
from typing import Any, Iterable, List, Mapping, NamedTuple, Sequence

from asts import lowered, visitor
from scope import Scope
from . import BYTE_ORDER, compress

SECTION_SEP = b"\x00" * 5
STRING_ENCODING = "UTF-8"
NATIVE_OP_CODES: Mapping[lowered.OperationTypes, int] = {
    lowered.OperationTypes.ADD: 1,
    lowered.OperationTypes.DIV: 2,
    lowered.OperationTypes.EQUAL: 3,
    lowered.OperationTypes.EXP: 4,
    lowered.OperationTypes.GREATER: 5,
    lowered.OperationTypes.JOIN: 6,
    lowered.OperationTypes.LESS: 7,
    lowered.OperationTypes.MOD: 8,
    lowered.OperationTypes.MUL: 9,
    lowered.OperationTypes.NEG: 10,
    lowered.OperationTypes.SUB: 11,
}


@unique
class OpCodes(Enum):
    """The numbers that identify different instructions."""

    LOAD_UNIT = 0
    LOAD_BOOL = 1
    LOAD_STRING = 2
    LOAD_INT = 3
    LOAD_FLOAT = 4

    LOAD_FUNC = 5
    BUILD_PAIR = 6
    BUILD_LIST = 7

    LOAD_NAME = 8
    STORE_NAME = 9

    APPLY = 10
    NATIVE = 11

    JUMP = 12
    BRANCH = 13


Instruction = NamedTuple(
    "Instruction", (("opcode", OpCodes), ("operands", tuple[Any, ...]))
)


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

    def visit_apply(self, node: lowered.Apply) -> Sequence[Instruction]:
        return (
            *node.arg.visit(self),
            *node.func.visit(self),
            Instruction(OpCodes.APPLY, ()),
        )

    def visit_block(self, node: lowered.Block) -> Sequence[Instruction]:
        self._push_scope()
        result = tuple(_chain(map(methodcaller("visit", self), node.body)))
        self._pop_scope()
        return result

    def visit_cond(self, node: lowered.Cond) -> Sequence[Instruction]:
        cons_body = node.cons.visit(self)
        else_body = node.else_.visit(self)
        return (
            *node.pred.visit(self),
            Instruction(OpCodes.BRANCH, (len(cons_body) + 1,)),
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

    def visit_function(self, node: lowered.Function) -> Sequence[Instruction]:
        self._push_scope()
        self.function_level += 1
        self.current_scope[node.param] = 0
        self.current_index += 1
        func_body = node.body.visit(self)
        self.function_level -= 1
        self._pop_scope()
        return (Instruction(OpCodes.LOAD_FUNC, (func_body,)),)

    def visit_list(self, node: lowered.List) -> Sequence[Instruction]:
        elements = tuple(node.elements)
        elem_instructions = tuple(_chain(map(self.run, elements)))
        return (
            *elem_instructions,
            Instruction(OpCodes.BUILD_LIST, (len(elements),)),
        )

    def visit_pair(self, node: lowered.Pair) -> Sequence[Instruction]:
        return (
            *node.second.visit(self),
            *node.first.visit(self),
            Instruction(OpCodes.BUILD_PAIR, ()),
        )

    def visit_name(self, node: lowered.Name) -> Sequence[Instruction]:
        if node not in self.current_scope:
            self.current_scope[node] = self.current_index
            self.current_index += 1

        depth = self.current_scope.depth(node)
        depth = 0 if self.function_level and depth else (depth + 1)
        position = self.current_scope[node]
        return (Instruction(OpCodes.LOAD_NAME, (depth, position)),)

    def visit_native_op(self, node: lowered.NativeOp) -> Sequence[Instruction]:
        right = () if node.right is None else node.right.visit(self)
        op_index = NATIVE_OP_CODES[node.operation]
        return (
            *right,
            *node.left.visit(self),
            Instruction(OpCodes.NATIVE, (op_index,)),
        )

    def visit_scalar(self, node: lowered.Scalar) -> Sequence[Instruction]:
        opcode: OpCodes = {
            bool: OpCodes.LOAD_BOOL,
            float: OpCodes.LOAD_FLOAT,
            int: OpCodes.LOAD_INT,
            str: OpCodes.LOAD_STRING,
        }[type(node.value)]
        return (Instruction(opcode, (node.value,)),)

    def visit_unit(self, node: lowered.Unit) -> Sequence[Instruction]:
        return (Instruction(OpCodes.LOAD_UNIT, ()),)


def to_bytecode(ast: lowered.LoweredASTNode, compress_code: bool = False) -> bytes:
    """
    Convert the high-level AST into a stream of bytes which can be
    written to a file or kept in memory.

    Parameters
    ----------
    ast: lowered.LoweredASTNode
        The high-level AST.
    compress_code: bool
        Whether to compress the code in order to achieve smaller
        file sizes.

    Returns
    -------
    bytes
        The resulting stream of bytes that represent the bytecode
        instruction objects.
    """
    instructions = InstructionGenerator().run(ast)
    stream, func_pool, string_pool = encode_instructions(instructions, [], [])
    funcs, strings = encode_pool(func_pool), encode_pool(string_pool)
    header = generate_header(len(stream), len(funcs), len(strings), STRING_ENCODING)
    return encode_all(header, stream, funcs, strings, compress_code)


def encode_pool(pool: Iterable[bytes]) -> bytes:
    """
    Convert a pool of objects into a stream of `bytes` so that they can
    be put into the bytecode stream.

    Parameters
    ----------
    pool: List[bytes]
        The list of objects to be encoded.

    Returns
    -------
    bytes
        A single `bytes` object that carries the entire pool in the
        order passed to the function.
    """
    convert = lambda item: len(item).to_bytes(4, BYTE_ORDER) + item
    return reduce(add, map(convert, pool), b"")


def generate_header(
    stream_size: int,
    func_pool_size: int,
    string_pool_size: int,
    encoding_used: str,
) -> bytes:
    """
    Create the header data for the bytecode file.

    Parameters
    ----------
    stream_size: int
        The length of the stream of bytecode instructions.
    func_pool_size: int
        The size of the function pool.
    string_pool_size: int
        The size of the string pool.
    encoding_used: str
        The encoding used to convert the strings in the string pool to
        `bytes`.

    Returns
    -------
    bytes
        The header data for the bytecode file.
    """
    encoding_name = lookup(encoding_used).name.encode("ASCII")
    return b"F:%bS:%bC:%bE:%b" % (
        func_pool_size.to_bytes(4, BYTE_ORDER),
        string_pool_size.to_bytes(4, BYTE_ORDER),
        stream_size.to_bytes(4, BYTE_ORDER),
        encoding_name.ljust(12, b"\x00"),
    )


def encode_all(
    header: bytes,
    stream: bytes,
    func_pool: bytes,
    string_pool: bytes,
    compress_code: bool,
) -> bytes:
    """
    Combine the various parts of the bytecode into a single byte string.

    Parameters
    ----------
    header: bytes
        The bytecode's header data.
    stream: bytes
        The actual bytecode instructions.
    func_pool: bytes
        The function pool.
    string_pool: bytes
        The string pool.
    compress_code: bool
         Whether to compress the bytecode in order to get a smaller
         file size.

    Returns
    -------
    bytes
        The full bytecode file as it should be passed to the VM.
    """
    body = b"".join((header, b"\xFF" * 3, func_pool, string_pool, stream))
    body, is_compressed = compress(body) if compress_code else (body, False)
    return (b"C\xFF" if compress_code and is_compressed else b"C\x00") + body


def encode_instructions(
    stream: Sequence[Instruction],
    func_pool: List[bytes],
    string_pool: List[bytes],
) -> tuple[bytearray, List[bytes], List[bytes]]:
    """
    Encode the bytecode stream as a single `bytes` object that can be
    written to file or kept in memory.

    Parameters
    ----------
    stream: Sequence[Instruction]
        The bytecode instruction objects to be encoded.
    func_pool: List[bytes]
        Where the generated bytecode for function objects is stored
        before being put in the final bytecode stream.
    string_pool: List[bytes]
        Where string objects are stored before being put in the final
        bytecode stream.

    Returns
    -------
    bytes
        The encoded stream of bytecode instructions. It is guaranteed
        to have a length proportional to the length of `stream`.
    """
    result_stream = bytearray(len(stream) * 8)
    for index, instruction in enumerate(stream):
        start = index * 8
        end = start + 8
        opcode_space = instruction.opcode.value.to_bytes(1, BYTE_ORDER)
        operand_space = encode_operands(
            instruction.opcode, instruction.operands, func_pool, string_pool
        )
        operand_space = operand_space.ljust(7, b"\x00")
        result_stream[start:end] = opcode_space + operand_space
    return result_stream, func_pool, string_pool


def encode_operands(
    opcode: OpCodes,
    operands: tuple[Any, ...],
    func_pool: List[bytes],
    string_pool: List[bytes],
) -> bytes:
    """
    Encode the operands of a single bytecode instruction.

    Parameters
    ----------
    opcode: OpCodes
        The type of bytecode instruction. This will be used to
        determine how to pack the operands.
    operands: tuple[Any, ...]
        The operands that will be turned into a `bytes` object.
    func_pool: List[bytes]
        Where the generated bytecode for function objects is stored
        before being put in the final bytecode stream.
    string_pool: List[bytes]
        Where string objects are stored before being put in the final
        bytecode stream.

    Returns
    -------
    bytes
        The resulting bytes. It is guaranteed to have a maximum length
        of 7 (the 8th byte is reserved for the opcode and will be
        prepended later on).
    """
    if opcode == OpCodes.LOAD_BOOL:
        return b"\xff" if operands[0] else b"\x00"
    if opcode == OpCodes.LOAD_STRING:
        return _encode_load_string(operands[0], string_pool)
    if opcode == OpCodes.LOAD_INT:
        return _encode_load_int(operands[0])
    if opcode == OpCodes.LOAD_FLOAT:
        return _encode_load_float(operands[0])
    if opcode == OpCodes.LOAD_NAME:
        return operands[0].to_bytes(3, BYTE_ORDER, signed=False) + operands[1].to_bytes(
            4, BYTE_ORDER, signed=False
        )
    if opcode == OpCodes.LOAD_FUNC:
        return _encode_load_func(operands[0], func_pool, string_pool)
    if opcode == OpCodes.STORE_NAME:
        return operands[0].to_bytes(4, BYTE_ORDER)
    if opcode == OpCodes.NATIVE:
        return operands[0].to_bytes(1, BYTE_ORDER)
    if opcode in (OpCodes.BRANCH, OpCodes.JUMP, OpCodes.BUILD_LIST):
        return operands[0].to_bytes(7, BYTE_ORDER)
    return b""


# TODO: Handle the `OverflowError`s raised by this function.
def _encode_load_int(value: int) -> bytes:
    return value.to_bytes(7, BYTE_ORDER, signed=True)


# TODO: Handle the `OverflowError`s raised by this function.
def _encode_load_float(value: float) -> bytes:
    data = Decimal(value).as_tuple()
    max_index = len(data.digits)
    digits = abs(
        sum(
            digit * (10 ** (max_index + 1 - index))
            for index, digit in enumerate(data.digits)
        )
    )
    digits = -digits if data.sign else digits
    exponent = abs(data.exponent)
    return digits.to_bytes(5, BYTE_ORDER, signed=True) + exponent.to_bytes(
        2, BYTE_ORDER, signed=True
    )


def _encode_load_string(string, string_pool):
    string_pool.append(string.encode(STRING_ENCODING))
    pool_index = len(string_pool) - 1
    return pool_index.to_bytes(7, BYTE_ORDER, signed=False)


def _encode_load_func(func_body, func_pool, string_pool):
    body_code, _, _ = encode_instructions(func_body, func_pool, string_pool)
    func_pool.append(body_code)
    pool_index = len(func_pool) - 1
    return pool_index.to_bytes(7, BYTE_ORDER)


def _chain(iterators):
    for iterator in iterators:
        yield from iterator

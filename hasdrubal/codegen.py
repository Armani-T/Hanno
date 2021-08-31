from collections import namedtuple
from enum import Enum, unique
from functools import reduce
from operator import add, methodcaller
from typing import Iterator, Sequence

from asts.base import VectorTypes
from asts.types import Type, TypeApply
from scope import Scope
from visitor import NodeVisitor
from asts import typed

Instruction = namedtuple("Instruction", ("opcode", "operands"))


@unique
class OpCodes(Enum):
    EXIT = 0

    LOAD_VAL = 1
    LOAD_VAR = 2

    BUILD_FUNC = 3
    BUILD_TUPLE = 4
    BUILD_LIST = 5

    CALL = 6

    STORE_VAR = 7

    SKIP = 8
    SKIP_FALSE = 9


class InstructionGenerator(NodeVisitor[Sequence[Instruction]]):
    """Turn the AST into a linear stream of bytecode instructions."""

    def __init__(self) -> None:
        self.current_index: int = 0
        self.prev_indexes: list[int] = []
        self.current_scope: Scope[int] = Scope(None)

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
        self.current_scope[node.param] = 0
        self.current_index += 1
        func_body = node.body.visit(self)
        self._pop_scope()
        return (Instruction(OpCodes.BUILD_FUNC, (0, func_body)),)

    def visit_name(self, node: typed.Scalar) -> Sequence[Instruction]:
        if node not in self.current_scope:
            self.current_scope[node] = self.current_index
            self.current_index += 1

        name_depth = self.current_scope.depth(node)
        name_index = self.current_scope[node]
        name_data = (name_depth, name_index)
        return (Instruction(OpCodes.LOAD_VAR, name_data),)

    def visit_scalar(self, node: typed.Scalar) -> Sequence[Instruction]:
        return (Instruction(OpCodes.LOAD_VAL, (node.value,)),)

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


def encode_instructions(stream: Iterator[Instruction]) -> bytes:
    """
    Encode the bytecode instruction objects given as a stream of bytes
    that can be written to a file or kept in memory.

    Parameters
    ----------
    stream: Iterator[Instruction]
        The bytecode instruction objects to be converted.

    Returns
    -------
    bytes
        The resulting stream of bytes.
    """

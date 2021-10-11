# pylint: disable=R0903, C0115, W0231
from abc import ABC
from enum import auto, Enum
from typing import cast, Iterable, Optional, Sequence

from . import base
from .types import Type, TypeApply, TypeName


class OperationTypes(Enum):
    """The different types of operations that are allowed in the AST."""

    ADD = "+"
    DIV = "/"
    EQUAL = "="
    EXP = "^"
    GREATER = ">"
    JOIN = "<>"
    LESS = "<"
    MUL = "*"
    NEG = "~"
    SUB = "-"


class LoweredASTNode(base.ASTNode):
    """
    The base for all the AST nodes which have been simplified to a
    level that is ready for bytecode generation.
    """


class FuncCall(LoweredASTNode):
    def __init__(
        self, span: base.Span, func: LoweredASTNode, args: list[LoweredASTNode]
    ) -> None:
        super().__init__(span)
        self.func: LoweredASTNode = func
        self.args: list[LoweredASTNode] = func

    def visit(self, visitor):
        return visitor.visit_func_call(self)


class Function(LoweredASTNode):
    def __init__(
        self, span: base.Span, params: list[LoweredASTNode], body: LoweredASTNode
    ) -> None:
        super().__init__(span)
        self.params: list[LoweredASTNode] = params
        self.body: LoweredASTNode = body

    def visit(self, visitor):
        return visitor.visit_function(self)


class NativeOperation(LoweredASTNode):
    def __init__(
        self,
        span: base.Span,
        operation: OperationTypes,
        left: LoweredASTNode,
        right: Optional[LoweredASTNode] = None,
    ) -> None:
        super().__init__(span)
        self.operation: OperationTypes = operation
        self.left: LoweredASTNode = left
        self.right: Optional[LoweredASTNode] = right

    def visit(self, visitor):
        return visitor.visit_native_operation(self)

# pylint: disable=R0903, C0115, W0231
from abc import ABC
from enum import Enum, unique
from typing import cast, Iterable, Optional, Sequence

from . import base
from .types import Type, TypeApply, TypeName


@unique
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


Block = base.Block
Cond = base.Cond
Define = base.Define
Name = base.Name
Scalar = base.Scalar
Vector = base.Vector


class FuncCall(base.ASTNode):
    def __init__(
        self, span: base.Span, func: LoweredASTNode, args: list[LoweredASTNode]
    ) -> None:
        super().__init__(span)
        self.func: LoweredASTNode = func
        self.args: list[LoweredASTNode] = func

    def visit(self, visitor):
        return visitor.visit_func_call(self)


class Function(base.ASTNode):
    def __init__(
        self, span: base.Span, params: list[LoweredASTNode], body: LoweredASTNode
    ) -> None:
        super().__init__(span)
        self.params: list[LoweredASTNode] = params
        self.body: LoweredASTNode = body

    def visit(self, visitor):
        return visitor.visit_function(self)


class NativeOperation(base.ASTNode):
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

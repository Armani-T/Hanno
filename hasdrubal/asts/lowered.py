# pylint: disable=R0903, C0115, W0231
from enum import Enum, unique
from typing import Optional

from . import base

LoweredASTNode = base.ASTNode
Block = base.Block
Cond = base.Cond
Define = base.Define
Name = base.Name
Scalar = base.Scalar
Vector = base.Vector


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

    @classmethod
    def __contains__(cls, item) -> bool:
        try:
            cls(item)
            return True
        except ValueError:
            return False


class FuncCall(LoweredASTNode):
    def __init__(
        self, span: base.Span, func: LoweredASTNode, args: list[LoweredASTNode]
    ) -> None:
        super().__init__(span)
        self.func: LoweredASTNode = func
        self.args: list[LoweredASTNode] = args

    def visit(self, visitor):
        return visitor.visit_func_call(self)


class Function(LoweredASTNode):
    def __init__(
        self, span: base.Span, params: list[Name], body: LoweredASTNode
    ) -> None:
        super().__init__(span)
        self.params: list[Name] = params
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

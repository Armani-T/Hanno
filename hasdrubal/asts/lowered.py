# pylint: disable=R0903, C0115, W0231
from enum import Enum, unique
from typing import Sequence, Optional

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
    MOD = "%"
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
        self, span: base.Span, func: LoweredASTNode, args: Sequence[LoweredASTNode]
    ) -> None:
        super().__init__(span)
        self.func: LoweredASTNode = func
        self.args: Sequence[LoweredASTNode] = args

    def visit(self, visitor):
        return visitor.visit_func_call(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, FuncCall):
            args_equal = all(
                self_arg == other_arg
                for self_arg in self.args
                for other_arg in other.args
            )
            return args_equal and self.func == other.func
        return NotImplemented

    __hash__ = object.__hash__


class Function(LoweredASTNode):
    def __init__(
        self, span: base.Span, params: Sequence[Name], body: LoweredASTNode
    ) -> None:
        super().__init__(span)
        self.params: Sequence[Name] = params
        self.body: LoweredASTNode = body

    def visit(self, visitor):
        return visitor.visit_function(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Function):
            params_equal = all(
                self_arg == other_arg
                for self_arg in self.params
                for other_arg in other.params
            )
            return params_equal and self.body == other.body
        return NotImplemented

    __hash__ = object.__hash__


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

    def __eq__(self, other) -> bool:
        if isinstance(other, NativeOperation):
            return (
                self.operation == other.operation
                and self.left == other.left
                and self.right == other.right
            )
        return NotImplemented

    __hash__ = object.__hash__

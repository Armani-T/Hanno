# pylint: disable=R0903, C0115, W0231
from abc import ABC
from collections import defaultdict
from enum import Enum, unique
from typing import Any, MutableMapping, Sequence, Optional, Union

from .base import ASTNode


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


class LoweredASTNode(ASTNode, ABC):
    def __init__(self) -> None:
        super().__init__((0, 0))
        self.metadata: MutableMapping[str, Any] = defaultdict(lambda: None)


class Apply(LoweredASTNode):
    __slots__ = ("args", "func", "metadata")

    def __init__(self, func: LoweredASTNode, arg: LoweredASTNode) -> None:
        super().__init__()
        self.func: LoweredASTNode = func
        self.arg: LoweredASTNode = arg

    def visit(self, visitor):
        return visitor.visit_apply(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Apply):
            return self.func == other.func and self.arg == other.arg
        return NotImplemented

    __hash__ = object.__hash__


class Block(LoweredASTNode):
    __slots__ = ("body", "metadata")

    def __init__(self, body: Sequence[LoweredASTNode]) -> None:
        if not body:
            raise ValueError("A block cannot have 0 expressions inside.")

        super().__init__()
        self.body: Sequence[LoweredASTNode] = body

    @classmethod
    def new(cls, body: Sequence[LoweredASTNode]):
        """
        Create a block of code or `Unit` depending on the number of
        instructions.
        """
        if not body:
            return Unit()
        if len(body) == 1:
            return body[0]
        return cls(body)

    def visit(self, visitor):
        return visitor.visit_block(self)

    def __eq__(self, other):
        if isinstance(other, Block):
            return all(
                self_elem == other_elem
                for self_elem, other_elem in zip(self.body, other.body)
            )
        return NotImplemented

    __hash__ = object.__hash__


class Cond(LoweredASTNode):
    __slots__ = ("cons", "else_", "pred", "metadata")

    def __init__(
        self, pred: LoweredASTNode, cons: LoweredASTNode, else_: LoweredASTNode
    ) -> None:
        super().__init__()
        self.pred: LoweredASTNode = pred
        self.cons: LoweredASTNode = cons
        self.else_: LoweredASTNode = else_

    def visit(self, visitor):
        return visitor.visit_cond(self)

    def __eq__(self, other):
        return (
            isinstance(other, Cond)
            and self.pred == other.pred
            and self.cons == other.cons
            and self.else_ == other.else_
        )

    __hash__ = object.__hash__


class Define(LoweredASTNode):
    __slots__ = ("target", "value", "metadata")

    def __init__(self, target: "Name", value: LoweredASTNode) -> None:
        super().__init__()
        self.target: Name = target
        self.value: LoweredASTNode = value

    def visit(self, visitor):
        return visitor.visit_define(self)

    def __eq__(self, other):
        return (
            isinstance(other, Define)
            and self.target == other.target
            and self.value == other.value
        )

    __hash__ = object.__hash__


class Function(LoweredASTNode):
    __slots__ = ("body", "param", "metadata")

    def __init__(self, param: "Name", body: LoweredASTNode) -> None:
        super().__init__()
        self.param: Name = param
        self.body: LoweredASTNode = body

    def visit(self, visitor):
        return visitor.visit_function(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Function):
            return self.param == other.param and self.body == other.body
        return NotImplemented

    __hash__ = object.__hash__


class List(LoweredASTNode):
    __slots__ = ("elements", "metadata")

    def __init__(self, elements: Sequence[LoweredASTNode]) -> None:
        super().__init__()
        self.elements: Sequence[LoweredASTNode] = elements

    def visit(self, visitor):
        return visitor.visit_list(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, List) and tuple(self.elements) == tuple(other.elements)

    __hash__ = object.__hash__


class Pair(LoweredASTNode):
    __slots__ = ("first", "second", "metadata")

    def __init__(self, first: LoweredASTNode, second: LoweredASTNode) -> None:
        super().__init__()
        self.first: LoweredASTNode = first
        self.second: LoweredASTNode = second

    def visit(self, visitor):
        return visitor.visit_pair(self)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Pair)
            and self.first == other.first
            and self.second == other.second
        )

    __hash__ = object.__hash__


class Name(LoweredASTNode):
    __slots__ = ("value", "metadata")

    def __init__(self, value: str) -> None:
        super().__init__()
        self.value: str = value

    def visit(self, visitor) -> None:
        return visitor.visit_name(self)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        if isinstance(other, Name):
            return self.value == other.value
        return NotImplemented

    __hash__ = object.__hash__


class NativeOp(LoweredASTNode):
    __slots__ = ("left", "operation", "right", "metadata")

    def __init__(
        self,
        operation: OperationTypes,
        left: LoweredASTNode,
        right: Optional[LoweredASTNode] = None,
    ) -> None:
        super().__init__()
        self.operation: OperationTypes = operation
        self.left: LoweredASTNode = left
        self.right: Optional[LoweredASTNode] = right

    def visit(self, visitor):
        return visitor.visit_native_op(self)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, NativeOp)
            and self.operation == other.operation
            and self.left == other.left
            and self.right == other.right
        )

    __hash__ = object.__hash__


class Scalar(LoweredASTNode):
    __slots__ = ("value", "metadata")

    def __init__(self, value: Union[str, int, float, bool]) -> None:
        super().__init__()
        self.value: Union[str, int, float, bool] = value

    def visit(self, visitor):
        return visitor.visit_scalar(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, Scalar) and self.value == other.value

    __hash__ = object.__hash__


class Unit(LoweredASTNode):
    __slots__ = ("metadata",)

    def visit(self, visitor):
        return visitor.visit_unit(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, Unit)

    __hash__ = object.__hash__

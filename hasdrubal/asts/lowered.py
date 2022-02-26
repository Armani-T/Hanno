# pylint: disable=R0903, C0115, W0231
from abc import ABC
from collections import defaultdict
from enum import Enum, unique
from typing import Any, MutableMapping, Sequence, Optional, Union

from .base import ASTNode


@unique
class ValueTypes(Enum):
    POINTER = 0
    UNIT = 1
    BOOL = 2
    INT = 3
    FLOAT = 4
    STRING = 5
    LIST = 6
    TUPLE = 7
    FUNCTION = 8


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

    def __init__(self, func: LoweredASTNode, args: Sequence[LoweredASTNode]) -> None:
        super().__init__()
        self.func: LoweredASTNode = func
        self.args: Sequence[LoweredASTNode] = args

    def visit(self, visitor):
        return visitor.visit_apply(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Apply):
            args_equal = all(
                self_arg == other_arg
                for self_arg in self.args
                for other_arg in other.args
            )
            return args_equal and self.func == other.func
        return NotImplemented

    __hash__ = object.__hash__


class Block(LoweredASTNode):
    __slots__ = ("body", "metadata")

    def __init__(self, body: Sequence[LoweredASTNode]) -> None:
        if not body:
            raise ValueError("A block cannot have 0 expressions inside.")

        super().__init__()
        self.body: Sequence[LoweredASTNode] = body

    def visit(self, visitor):
        return visitor.visit_block(self)

    def __eq__(self, other):
        return isinstance(other, Block) and self.body == other.body

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
    __slots__ = ("body", "params", "metadata")

    def __init__(self, params: Sequence["Name"], body: LoweredASTNode) -> None:
        """
        Note that it is assumed that all the names in `params` have
        their `type_` attrs set to a value from `ValueTypes`.
        """
        super().__init__()
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


class Name(LoweredASTNode):
    __slots__ = ("value", "metadata")

    def __init__(self, value: str, type_: Optional[ValueTypes] = None) -> None:
        super().__init__()
        self.value: str = value
        self.metadata["type_"] = type_

    def visit(self, visitor) -> None:
        return visitor.visit_name(self)

    def __eq__(self, other):
        return isinstance(other, Name) and self.value == other.value

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


class Tuple(LoweredASTNode):
    __slots__ = ("elements", "metadata")

    def __init__(self, elements: Sequence[LoweredASTNode]) -> None:
        if len(elements) >= 256:
            raise ValueError("Tuples cannot have more than 255 elements.")

        super().__init__()
        self.elements: Sequence[LoweredASTNode] = elements
        self.metadata["length"] = len(elements)

    def visit(self, visitor):
        return visitor.visit_tuple(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, Tuple) and tuple(self.elements) == tuple(
            other.elements
        )

    __hash__ = object.__hash__

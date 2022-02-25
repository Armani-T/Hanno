# pylint: disable=R0903, C0115, W0231
from abc import ABC
from enum import Enum, unique
from typing import Any, MutableMapping, Sequence, Optional, Tuple, Union

from .base import ASTNode, VectorTypes


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
        self._metadata: MutableMapping[str, Any] = {}

    def __getattr__(self, name):
        try:
            return super().__getattr__(self, name)
        except AttributeError:
            result = self._metadata.get(name, None)
            if result is None:
                raise
            return result


class Block(LoweredASTNode):
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


class FuncCall(LoweredASTNode):
    def __init__(self, func: LoweredASTNode, args: Sequence[LoweredASTNode]) -> None:
        super().__init__()
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
        self, params: Sequence[Tuple["Name", OperationTypes]], body: LoweredASTNode
    ) -> None:
        super().__init__()
        self.params: Sequence[Tuple[Name, OperationTypes]] = params
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


class Name(LoweredASTNode):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value: str = value

    def visit(self, visitor) -> None:
        return self.visif_name(self)

    def __eq__(self, other):
        return isinstance(other, Name) and self.value == other.value

    __hash__ = object.__hash__


class NativeOperation(LoweredASTNode):
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
        return visitor.visit_native_operation(self)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, NativeOperation)
            and self.operation == other.operation
            and self.left == other.left
            and self.right == other.right
        )

    __hash__ = object.__hash__


class Scalar(LoweredASTNode):
    def __init__(self, value: Union[str, int, float, bool]) -> None:
        super().__init__()
        self.value: Union[str, int, float, bool] = value

    def visit(self, visitor):
        return visitor.visit_scalar(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, Scalar) and self.value == other.value

    __hash__ = object.__hash__


class Vector(LoweredASTNode):
    def __init__(
        self, vec_type: VectorTypes, elements: Sequence[LoweredASTNode]
    ) -> None:
        super().__init__()
        self.vec_type: VectorTypes = vec_type
        self.elements: Sequence[LoweredASTNode] = elements

    def visit(self, visitor):
        return visitor.visit_vector(self)

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Vector)
            and self.vec_type == other.vec_type
            and tuple(self.elements) == tuple(other.elements)
        )

    __hash__ = object.__hash__

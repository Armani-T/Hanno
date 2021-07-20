# pylint: disable=R0903
from abc import ABC, abstractmethod
from enum import auto, Enum
from typing import final, Iterable, Optional, Reversible, Sequence, Tuple


def merge(left_span: Tuple[int, int], right_span: Tuple[int, int]) -> Tuple[int, int]:
    start = min(left_span[0], right_span[0])
    end = max(left_span[1], right_span[1])
    return (start, end)


class ScalarTypes(Enum):
    """The different types of scalars that are allowed in the AST."""

    BOOL = auto()
    FLOAT = auto()
    INTEGER = auto()
    STRING = auto()


class VectorTypes(Enum):
    """The different types of vectors that are allowed in the AST."""

    LIST = auto()
    TUPLE = auto()


class ASTNode(ABC):
    """
    The base of all the nodes used in the AST.

    Attributes
    ----------
    span: Tuple[int, int]
        The position in the source text that this AST node came from.
    type_: Optional[Type]
        The type of the value that this AST node will eventually
        evaluate to (default: `None`).
    """

    def __init__(self, span: Tuple[int, int]) -> None:
        self.span: Tuple[int, int] = span
        self.type_: Optional["Type"] = None

    @abstractmethod
    def visit(self, visitor):
        """Run `visitor` on this node by selecting the correct node."""


class Block(ASTNode):
    __slots__ = ("first", "rest", "span", "type_")

    def __init__(self, span: Tuple[int, int], body: Sequence[ASTNode]) -> None:
        super().__init__(span)
        self.first: ASTNode = body[0]
        self.rest: Iterable[ASTNode] = body[1:]

    def visit(self, visitor):
        return visitor.visit_block(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Block):
            return self.first == other.first and self.rest == other.rest
        return NotImplemented


class Cond(ASTNode):
    __slots__ = ("cons", "else_", "pred", "span", "type_")

    def __init__(
        self, span: Tuple[int, int], pred: ASTNode, cons: ASTNode, else_: ASTNode
    ) -> None:
        super().__init__(span)
        self.pred: ASTNode = pred
        self.cons: ASTNode = cons
        self.else_: ASTNode = else_

    def visit(self, visitor):
        return visitor.visit_cond(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Cond):
            return (
                self.pred == other.pred
                and self.cons == other.cons
                and self.else_ == other.else_
            )
        return NotImplemented


class Define(ASTNode):
    __slots__ = ("body", "span", "target", "type_", "value")

    def __init__(
        self,
        span: Tuple[int, int],
        target: "Name",
        value: ASTNode,
        body: Optional[ASTNode] = None,
    ) -> None:
        super().__init__(span)
        self.target: Name = target
        self.value: ASTNode = value
        self.body: Optional[ASTNode] = body

    def visit(self, visitor):
        return visitor.visit_define(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Define):
            return (
                self.target == other.target
                and self.value == other.value
                and self.body == other.body
            )
        return NotImplemented


class FuncCall(ASTNode):
    __slots__ = ("callee", "callee", "span", "type_")

    def __init__(self, caller: ASTNode, callee: ASTNode) -> None:
        super().__init__(merge(caller.span, callee.span))
        self.caller: ASTNode = caller
        self.callee: ASTNode = callee

    def visit(self, visitor):
        return visitor.visit_func_call(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, FuncCall):
            return self.caller == other.caller and self.callee == other.callee
        return NotImplemented


class Function(ASTNode):
    __slots__ = ("body", "param", "span", "type_")

    def __init__(self, span: Tuple[int, int], param: "Name", body: ASTNode) -> None:
        super().__init__(span)
        self.param: Name = param
        self.body: ASTNode = body

    @classmethod
    def curry(cls, span: Tuple[int, int], params: Reversible["Name"], body: ASTNode):
        """
        Make a function which takes any number of arguments at once
        into a series of nested ones that takes one arg at a time.

        Warnings
        --------
        - This function assumes that the params list has been checked
          to ensure it isn't empty.
        """
        for param in reversed(params):
            body = cls(span, param, body)
        return body

    def visit(self, visitor):
        return visitor.visit_function(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Function):
            return self.param == other.param and self.body == other.body
        return NotImplemented


class Name(ASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(self, span: Tuple[int, int], value: Optional[str]) -> None:
        if value is None:
            raise TypeError("`value` is supposed to be a string, not None.")

        super().__init__(span)
        self.value: str = value

    def visit(self, visitor):
        return visitor.visit_name(self)

    def __eq__(self, other):
        if isinstance(other, Name):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)


class Scalar(ASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(
        self,
        span: Tuple[int, int],
        scalar_type: ScalarTypes,
        value_string: Optional[str],
    ) -> None:
        if value_string is None:
            raise TypeError("`value_string` is supposed to be a string, not None.")

        super().__init__(span)
        self.scalar_type: ScalarTypes = scalar_type
        self.value_string: str = value_string

    def visit(self, visitor):
        return visitor.visit_scalar(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Scalar):
            return (
                self.scalar_type == other.scalar_type
                and self.value_string == other.value_string
            )
        return NotImplemented


class Type(ASTNode, ABC):
    """
    This is the base class for the program's representation of types in
    the type system.

    Warnings
    --------
    - This class should not be used directly, instead use one of its
      subclasses.
    """

    @final
    def visit(self, visitor):
        return visitor.visit_type(self)


class FuncType(Type):
    """
    This is the type of a function for the type system.

    Attributes
    ----------
    left: Type
        The type of the single argument to the function.
    right: Type
        The type of what the function's return.
    """

    __slots__ = ("left", "span", "right", "type_")

    def __init__(self, span: Tuple[int, int], left: Type, right: Type) -> None:
        super().__init__(span)
        self.left: Type = left
        self.right: Type = right

    def __eq__(self, other) -> bool:
        if isinstance(other, FuncType):
            return self.left == other.left and self.right == other.right
        return NotImplemented


class GenericType(Type):

    __slots__ = ("args", "base", "span", "type_")

    def __init__(
        self, span: Tuple[int, int], base: Name, args: Sequence[Type] = ()
    ) -> None:
        super().__init__(span)
        self.base: Name = base
        self.args: Sequence[Type] = args

    def __eq__(self, other):
        if isinstance(other, GenericType):
            return self.base == other.base and tuple(self.args) == tuple(other.args)
        return NotImplemented


class TypeScheme(Type):
    __slots__ = ("bound", "span", "type_")

    def __init__(self, type_: Type, bound_types: set["TypeVar"]) -> None:
        super().__init__(type_.span)
        self.type_: Type = type_
        self.bound_types: set[TypeVar] = bound_types

    def __eq__(self, other) -> bool:
        if isinstance(self, TypeScheme):
            return self.type_ == other.type_ and self.bound_types == other.bound_types
        return NotImplemented


class TypeVar(Type):

    __slots__ = ("span", "type_", "value")
    n_type_vars = 0

    def __init__(self, span: Tuple[int, int], value: str) -> None:
        super().__init__(span)
        self.value: str = value

    @classmethod
    def unknown(cls, span: Tuple[int, int]):
        """
        Make a type var instance without explicitly providing a name
        for it.

        Attribute
        ---------
        span: Tuple[int, int]
            The position of this instance in the source code.
        """
        cls.n_type_vars += 1
        return cls(span, str(cls.n_type_vars))

    def __eq__(self, other) -> bool:
        if isinstance(other, TypeVar):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)


class Vector(ASTNode):
    __slots__ = ("elements", "span", "type_", "vec_type")

    def __init__(
        self, span: Tuple[int, int], vec_type: VectorTypes, elements: Iterable[ASTNode]
    ) -> None:
        super().__init__(span)
        self.vec_type: VectorTypes = vec_type
        self.elements: Iterable[ASTNode] = elements

    @classmethod
    def unit(cls, span: Tuple[int, int]):
        return cls(span, VectorTypes.TUPLE, ())

    def visit(self, visitor):
        return visitor.visit_vector(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Vector):
            return self.vec_type == other.vec_type and tuple(self.elements) == tuple(
                other.elements
            )
        return NotImplemented

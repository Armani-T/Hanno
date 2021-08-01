# pylint: disable=R0903
from abc import ABC, abstractmethod
from enum import auto, Enum
from typing import Iterable, Optional, Sequence

Span = tuple[int, int]


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
    span: Span
        The position in the source text that this AST node came from.
    """

    def __init__(self, span: Span) -> None:
        self.span: Span = span

    @abstractmethod
    def visit(self, visitor):
        """Run `visitor` on this node by selecting the correct node."""


class Block(ASTNode):
    __slots__ = ("first", "rest", "span")

    def __init__(self, span: Span, body: Sequence[ASTNode]) -> None:
        super().__init__(span)
        self.first: ASTNode = body[0]
        self.rest: Sequence[ASTNode] = body[1:]

    def visit(self, visitor):
        return visitor.visit_block(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Block):
            return self.first == other.first and self.rest == other.rest
        return NotImplemented

    __hash__ = object.__hash__


class Cond(ASTNode):
    __slots__ = ("cons", "else_", "pred", "span")

    def __init__(
        self, span: Span, pred: ASTNode, cons: ASTNode, else_: ASTNode
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

    __hash__ = object.__hash__


class Define(ASTNode):
    __slots__ = ("body", "span", "target", "value")

    def __init__(
        self,
        span: Span,
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

    __hash__ = object.__hash__


class FuncCall(ASTNode):
    __slots__ = ("callee", "callee", "span")

    def __init__(self, span: Span, caller: ASTNode, callee: ASTNode) -> None:
        super().__init__(span)
        self.caller: ASTNode = caller
        self.callee: ASTNode = callee

    def visit(self, visitor):
        return visitor.visit_func_call(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, FuncCall):
            return self.caller == other.caller and self.callee == other.callee
        return NotImplemented

    __hash__ = object.__hash__


class Function(ASTNode):
    __slots__ = ("body", "param", "span")

    def __init__(self, span: Span, param: "Name", body: ASTNode) -> None:
        super().__init__(span)
        self.param: Name = param
        self.body: ASTNode = body

    @classmethod
    def curry(cls, span: Span, params: Iterable["Name"], body: ASTNode):
        """
        Make a function which takes any number of arguments at once
        into a series of nested ones that takes one arg at a time.

        Warnings
        --------
        - This function assumes that the params list has been checked
          to ensure it isn't empty.
        """
        if not params:
            return body

        first, *rest = params
        return (
            cls(span, first, cls.curry(span, rest, body))
            if rest
            else cls(span, first, body)
        )

    def visit(self, visitor):
        return visitor.visit_function(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Function):
            return self.param == other.param and self.body == other.body
        return NotImplemented

    __hash__ = object.__hash__


class Name(ASTNode):
    __slots__ = ("span", "value")

    def __init__(self, span: Span, value: Optional[str]) -> None:
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
    __slots__ = ("span", "value")

    def __init__(
        self,
        span: Span,
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

    __hash__ = object.__hash__


class Vector(ASTNode):
    __slots__ = ("elements", "span", "vec_type")

    def __init__(
        self, span: Span, vec_type: VectorTypes, elements: Iterable[ASTNode]
    ) -> None:
        super().__init__(span)
        self.vec_type: VectorTypes = vec_type
        self.elements: Iterable[ASTNode] = elements

    @classmethod
    def unit(cls, span: Span):
        return cls(span, VectorTypes.TUPLE, ())

    def visit(self, visitor):
        return visitor.visit_vector(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Vector):
            return self.vec_type == other.vec_type and tuple(self.elements) == tuple(
                other.elements
            )
        return NotImplemented

    __hash__ = object.__hash__

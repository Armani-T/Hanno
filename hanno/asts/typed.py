# pylint: disable=R0903, C0115, W0231
from abc import ABC
from typing import Iterable, Optional, Sequence, Tuple

from . import base
from .types_ import Type, TypeName


class TypedASTNode(base.ASTNode, ABC):
    """
    The base of all the nodes used in the AST but now with type
    annotations for all of them.

    Attributes
    ----------
    type_: Optional[Type]
        The type of the value that this AST node will evaluate to.
    """

    def __init__(self, span: base.Span, type_: Type) -> None:
        super().__init__(span)
        self.type_: Type = type_


class Apply(base.Apply, TypedASTNode):
    __slots__ = ("arg", "func", "span", "type_")

    def __init__(
        self, span: base.Span, type_: Type, func: TypedASTNode, arg: TypedASTNode
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.func: TypedASTNode = func
        self.arg: TypedASTNode = arg


class Block(base.Block, TypedASTNode):
    __slots__ = ("body", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        body: Sequence[TypedASTNode],
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.body: Sequence[TypedASTNode] = body


class Cond(base.Cond, TypedASTNode):
    __slots__ = ("cons", "else_", "pred", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        pred: TypedASTNode,
        cons: TypedASTNode,
        else_: TypedASTNode,
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.pred: TypedASTNode = pred
        self.cons: TypedASTNode = cons
        self.else_: TypedASTNode = else_


class Define(base.Define, TypedASTNode):
    __slots__ = ("span", "target", "type_", "value")

    def __init__(
        self, span: base.Span, type_: Type, target: base.Pattern, value: TypedASTNode
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.target: base.Pattern = target
        self.value: TypedASTNode = value


class Function(base.Function, TypedASTNode):
    __slots__ = ("body", "param", "span", "type_")

    def __init__(
        self, span: base.Span, type_: Type, param: base.Pattern, body: TypedASTNode
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.param: base.Pattern = param
        self.body: TypedASTNode = body


class List(base.List, TypedASTNode):
    __slots__ = ("elements", "span", "type_")

    def __init__(
        self, span: base.Span, type_: Type, elements: Iterable[TypedASTNode]
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.elements: Iterable[TypedASTNode] = elements


class Match(base.Match, TypedASTNode):
    __slots__ = ("cases", "span", "subject")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        subject: TypedASTNode,
        cases: Iterable[Tuple[base.Pattern, TypedASTNode]],
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.subject: TypedASTNode = subject
        self.cases: Iterable[Tuple[base.Pattern, TypedASTNode]] = cases


class Pair(base.Pair, TypedASTNode):
    __slots__ = ("first", "second", "span", "type_")

    def __init__(
        self, span: base.Span, type_: Type, first: TypedASTNode, second: TypedASTNode
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.first: TypedASTNode = first
        self.second: TypedASTNode = second


class Name(base.Name, TypedASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(self, span: base.Span, type_: Type, value: Optional[str]) -> None:
        if value is None:
            raise TypeError("`None` was passed to `typed.Name.__init__`.")

        TypedASTNode.__init__(self, span, type_)
        self.value: str = value


class Scalar(base.Scalar, TypedASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(
        self,
        span: base.Span,
        type_: TypeName,
        value: base.ValidScalarTypes,
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.value: base.ValidScalarTypes = value


class Unit(base.Unit, TypedASTNode):
    __slots__ = ("span", "type_")

    def __init__(self, span: base.Span, type_: Type = None) -> None:
        TypedASTNode.__init__(self, span, type_ or TypeName.unit(span))

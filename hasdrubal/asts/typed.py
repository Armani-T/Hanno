# pylint: disable=R0903
from abc import ABC
from typing import Iterable, Optional, Sequence

from . import base
from .types import Type, TypeApply, TypeName


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


class Block(base.Block, TypedASTNode):
    __slots__ = ("first", "rest", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        body: Sequence[TypedASTNode],
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.first: TypedASTNode = body[0]
        self.rest: Sequence[TypedASTNode] = body[1:]


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
        self, span: base.Span, type_: Type, target: "Name", value: TypedASTNode
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.target: Name = target
        self.value: TypedASTNode = value


class FuncCall(base.FuncCall, TypedASTNode):
    __slots__ = ("callee", "callee", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        caller: TypedASTNode,
        callee: TypedASTNode,
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.caller: TypedASTNode = caller
        self.callee: TypedASTNode = callee


class Function(base.Function, TypedASTNode):
    __slots__ = ("body", "param", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        param: "Name",
        body: TypedASTNode,
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.param: Name = param
        self.body: TypedASTNode = body

    @classmethod
    def curry(cls, span: base.Span, params: Iterable["Name"], body: TypedASTNode):
        if not params:
            return body

        first, *rest = params
        if not rest:
            return cls(span, TypeApply.func(span, first.type_, body.type_), first, body)
        return cls(
            span,
            TypeApply.func(span, first.type_, body.type_),
            first,
            cls.curry(span, rest, body),
        )


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
        scalar_type: base.ScalarTypes,
        value_string: Optional[str],
    ) -> None:
        if value_string is None:
            raise TypeError("`None` was passed to `typed.Scalar.__init__`.")

        TypedASTNode.__init__(self, span, type_)
        self.scalar_type: base.ScalarTypes = scalar_type
        self.value_string: str = value_string


class Vector(base.Vector, TypedASTNode):
    __slots__ = ("elements", "span", "type_", "vec_type")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        vec_type: base.VectorTypes,
        elements: Iterable[TypedASTNode],
    ) -> None:
        TypedASTNode.__init__(self, span, type_)
        self.vec_type: base.VectorTypes = vec_type
        self.elements: Iterable[TypedASTNode] = elements

    @classmethod
    def unit(cls, span: base.Span):
        return cls(span, TypeName.unit(span), base.VectorTypes.TUPLE, ())

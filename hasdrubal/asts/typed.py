# pylint: disable=R0903
from abc import ABC
from typing import Iterable, Optional, Reversible, Sequence

from . import base
from .types import FuncType, GenericType, Type


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
        super().__init__(base.Span)
        self.type_: "Type" = type_


class Block(base.Block, TypedASTNode):
    __slots__ = ("first", "rest", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        body: Sequence[TypedASTNode],
    ) -> None:
        TypedASTNode.__init__(self, base.Span, type_)
        base.Block.__init__(self, base.Span, body)


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
        TypedASTNode.__init__(self, base.Span, type_)
        base.Cond.__init__(self, base.Span, pred, cons, else_)


class Define(base.Define, TypedASTNode):
    __slots__ = ("body", "span", "target", "type_", "value")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        target: "Name",
        value: TypedASTNode,
        body: Optional[TypedASTNode] = None,
    ) -> None:
        TypedASTNode.__init__(self, base.Span, type_)
        base.Define.__init__(self, base.Span, target, value, body)


class FuncCall(base.FuncCall, TypedASTNode):
    __slots__ = ("callee", "callee", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        caller: TypedASTNode,
        callee: TypedASTNode,
    ) -> None:
        TypedASTNode.__init__(self, base.Span, type_)
        base.FuncCall.__init__(self, base.Span, caller, callee)


class Function(base.Function, TypedASTNode):
    __slots__ = ("body", "param", "span", "type_")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        param: "Name",
        body: TypedASTNode,
    ) -> None:
        TypedASTNode.__init__(self, base.Span, type_)
        base.Function.__init__(self, base.Span, param, body)

    @classmethod
    def curry(
        cls, span: base.Span, params: Reversible["Name"], body: TypedASTNode
    ):
        for param in reversed(params):
            body = cls(
                base.Span,
                FuncType(base.Span, param.type_, body.type_),
                param,
                body,
            )
        return body


class Name(base.Name, TypedASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(
        self, span: base.Span, type_: Type, value: Optional[str]
    ) -> None:
        TypedASTNode.__init__(self, base.Span, type_)
        base.Name.__init__(self, base.Span, value)


class Scalar(base.Scalar, TypedASTNode):
    __slots__ = ("span", "type_", "value")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        scalar_type: base.ScalarTypes,
        value_string: Optional[str],
    ) -> None:
        TypedASTNode.__init__(self, base.Span, type_)
        base.Scalar.__init__(self, base.Span, scalar_type, value_string)


class Vector(base.Vector, TypedASTNode):
    __slots__ = ("elements", "span", "type_", "vec_type")

    def __init__(
        self,
        span: base.Span,
        type_: Type,
        vec_type: base.VectorTypes,
        elements: Iterable[TypedASTNode],
    ) -> None:
        TypedASTNode.__init__(self, base.Span, type_)
        base.Vector.__init__(self, base.Span, vec_type, elements)

    @classmethod
    def unit(cls, span: base.Span):
        return cls(
            base.Span,
            GenericType(base.Span, base.Name(base.Span, "Unit")),
            base.VectorTypes.TUPLE,
            (),
        )

# pylint: disable=R0903, C0115
from typing import AbstractSet, final, Sequence

from .base import ASTNode, Span

TVarSet = AbstractSet["TypeVar"]


class Type(ASTNode):
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


class TypeApply(Type):
    __slots__ = ("callee", "caller", "span", "type_")

    def __init__(self, span: Span, caller: Type, callee: Type) -> None:
        super().__init__(span)
        self.caller: Type = caller
        self.callee: Type = callee

    @classmethod
    def func(cls, span: Span, arg_type: Type, return_type: Type):
        """Build a function type."""
        return cls(span, cls(span, TypeName(span, "->"), arg_type), return_type)

    @classmethod
    def tuple_(cls, span: Span, args: Sequence[Type]):
        """Build an N-tuple type where `N = len(args)`."""
        result, *args = args
        for index, arg in enumerate(args):
            result = cls(
                span,
                result if index % 2 else cls(span, TypeName(span, ","), result),
                arg,
            )
        return result

    def __eq__(self, other) -> bool:
        if isinstance(other, TypeApply):
            return self.caller == other.caller and self.callee == other.callee
        return NotImplemented

    __hash__ = object.__hash__


class TypeName(Type):
    __slots__ = ("span", "value")

    def __init__(self, span: Span, value: str) -> None:
        super().__init__(span)
        self.value: str = value

    @classmethod
    def unit(cls, span: Span):
        return cls(span, "Unit")

    def __eq__(self, other) -> bool:
        if isinstance(other, TypeName):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)


class TypeScheme(Type):
    __slots__ = ("actual_type", "bound_type", "span", "type_")

    def __init__(self, actual_type: Type, bound_types: TVarSet) -> None:
        super().__init__(actual_type.span)
        self.actual_type: Type = actual_type
        self.bound_types: AbstractSet[TypeVar] = frozenset(bound_types)

    def __eq__(self, other) -> bool:
        if isinstance(other, TypeScheme):
            return self.actual_type == other.actual_type and len(
                self.bound_types
            ) == len(other.bound_types)
        return NotImplemented

    __hash__ = object.__hash__


class TypeVar(Type):

    __slots__ = ("span", "type_", "value")
    n_type_vars = 0

    def __init__(self, span: Span, value: str) -> None:
        super().__init__(span)
        self.value: str = value

    @classmethod
    def unknown(cls, span: Span):
        """
        Make a type var instance without explicitly providing a name
        for it.

        Attribute
        ---------
        span: Span
            The position of this instance in the source code.
        """
        cls.n_type_vars += 1
        return cls(span, str(cls.n_type_vars))

    def __eq__(self, other) -> bool:
        return isinstance(other, TypeVar)

    def __hash__(self) -> int:
        return hash(self.value)

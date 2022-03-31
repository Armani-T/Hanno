# pylint: disable=R0903, C0115
from abc import ABC, abstractmethod
from typing import AbstractSet, final, Sequence

from .base import ASTNode, Span


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

    @abstractmethod
    def __eq__(self, other) -> bool:
        ...

    @abstractmethod
    def __contains__(self, value) -> bool:
        ...


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
    def tuple_(cls, span: Span, elems: Sequence[Type]):
        """Build an N-tuple type where `N = len(args)`."""
        if not elems:
            return TypeName.unit(span)
        if len(elems) == 1:
            return elems[0]

        first, second, *elems = reversed(elems)
        result = cls(span, first, second)
        for elem in elems:
            result = cls(span, elem, result)
        return result

    def __eq__(self, other: "Type") -> bool:
        return (
            isinstance(other, TypeApply)
            and self.caller == other.caller
            and self.callee == other.callee
        )

    def __contains__(self, value) -> bool:
        return value in self.caller or value in self.callee

    def __repr__(self) -> str:
        return f"({repr(self.caller)} {repr(self.callee)})"

    __hash__ = object.__hash__


class TypeName(Type):
    __slots__ = ("span", "value")

    def __init__(self, span: Span, value: str) -> None:
        super().__init__(span)
        self.value: str = value

    @classmethod
    def unit(cls, span: Span):
        return cls(span, "Unit")

    def __eq__(self, other: "Type") -> bool:
        return isinstance(other, TypeName) and self.value == other.value

    def __contains__(self, value) -> bool:
        return False

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return self.value


class TypeScheme(Type):
    __slots__ = ("actual_type", "bound_type", "span", "type_")

    def __init__(self, actual_type: Type, bound_types: AbstractSet["TypeVar"]) -> None:
        super().__init__(actual_type.span)
        self.actual_type: Type = actual_type
        self.bound_types: AbstractSet[TypeVar] = frozenset(bound_types)

    def __eq__(self, other: "Type") -> bool:
        if isinstance(other, TypeScheme):
            type_equal = self.actual_type == other.actual_type
            size_equal = len(self.bound_types) == len(other.bound_types)
            return type_equal and size_equal
        return False

    def __contains__(self, value) -> bool:
        subs = {var: TypeVar.unknown(var.span) for var in self.bound_types}
        return value in self.actual_type.substitute(subs)

    def __repr__(self) -> str:
        return f"{', '.join(map(repr, self.bound_types))} . {repr(self.actual_type)}"

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

    def __eq__(self, other: "Type") -> bool:
        return isinstance(other, TypeVar)

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"@{self.value}"

    def __contains__(self, value) -> bool:
        return isinstance(value, TypeVar) and self.value == value.value

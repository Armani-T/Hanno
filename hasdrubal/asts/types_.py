# pylint: disable=R0903, C0115
from abc import ABC, abstractmethod
from typing import AbstractSet, Any, final, Mapping, Sequence

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
    def substitute(self, substitution: Mapping["TypeVar", "Type"]) -> "Type":
        """
        Replace free type vars in the object with the types in
        `substitution`.

        Parameters
        ----------
        substitution: Substitution
            The mapping to used to replace the free type vars.

        Returns
        -------
        Type
            The same object but without any free type variables.
        """

    @abstractmethod
    def strong_eq(self, other: "Type") -> bool:
        """A version of equality that comes with more guarantees."""

    @abstractmethod
    def weak_eq(self, other: "Type") -> bool:
        """A version of equality that comes with fewer guarantees."""

    @final
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Type):
            return self.weak_eq(other)
        return NotImplemented

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
    def tuple_(cls, span: Span, args: Sequence[Type]):
        """Build an N-tuple type where `N = len(args)`."""
        if not args:
            return TypeName.unit(span)

        result, *args = args
        for index, arg in enumerate(args):
            result = cls(
                span,
                result if index % 2 else cls(span, TypeName(span, "Tuple"), result),
                arg,
            )
        return result

    def substitute(self, substitution: Mapping["TypeVar", "Type"]) -> "Type":
        return TypeApply(
            self.span,
            self.caller.substitute(substitution),
            self.callee.substitute(substitution),
        )

    def strong_eq(self, other: "Type") -> bool:
        return (
            isinstance(other, TypeApply)
            and self.caller.strong_eq(other.caller)
            and self.callee.strong_eq(other.callee)
        )

    def weak_eq(self, other: "Type") -> bool:
        return (
            isinstance(other, TypeApply)
            and self.caller.weak_eq(other.caller)
            and self.callee.weak_eq(other.callee)
        )

    def __contains__(self, value) -> bool:
        return value in self.caller or value in self.callee

    __hash__ = object.__hash__


class TypeName(Type):
    __slots__ = ("span", "value")

    def __init__(self, span: Span, value: str) -> None:
        super().__init__(span)
        self.value: str = value

    @classmethod
    def unit(cls, span: Span):
        return cls(span, "Unit")

    def substitute(self, substitution: Mapping["TypeVar", "Type"]) -> "Type":
        return self

    def strong_eq(self, other: "Type") -> bool:
        return isinstance(other, TypeName) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    weak_eq = strong_eq
    __contains__ = strong_eq


class TypeScheme(Type):
    __slots__ = ("actual_type", "bound_type", "span", "type_")

    def __init__(self, actual_type: Type, bound_types: AbstractSet["TypeVar"]) -> None:
        super().__init__(actual_type.span)
        self.actual_type: Type = actual_type
        self.bound_types: AbstractSet[TypeVar] = frozenset(bound_types)

    def substitute(self, substitution: Mapping["TypeVar", "Type"]) -> "Type":
        new_sub = {
            var: value
            for var, value in substitution.items()
            if var not in self.bound_types
        }
        return TypeScheme(self.actual_type.substitute(new_sub), self.bound_types)

    def strong_eq(self, other: "Type") -> bool:
        if isinstance(other, TypeScheme):
            subs = {var: TypeVar.unknown(var.span) for var in self.bound_types}
            actual = self.actual_type.substitute(subs)
            return actual.strong_eq(other.actual_type.substitute(subs))
        return False

    def weak_eq(self, other: "Type") -> bool:
        if isinstance(other, TypeScheme):
            type_equal = self.actual_type == other.actual_type
            size_equal = len(self.bound_types) == len(other.bound_types)
            return type_equal and size_equal
        return False

    def __contains__(self, value) -> bool:
        subs = {var: TypeVar.unknown(var.span) for var in self.bound_types}
        return value in self.actual_type.substitute(subs)

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

    def substitute(self, substitution: Mapping["TypeVar", "Type"]) -> "Type":
        type_ = substitution.get(self, self)
        return (
            type_.substitute(substitution)
            if isinstance(type_, TypeVar) and type_ in substitution
            else type_
        )

    def strong_eq(self, other: "Type") -> bool:
        return isinstance(other, TypeVar) and self.value == other.value

    def weak_eq(self, other: "Type") -> bool:
        return isinstance(other, TypeVar)

    def __hash__(self) -> int:
        return hash(self.value)

    __contains__ = strong_eq

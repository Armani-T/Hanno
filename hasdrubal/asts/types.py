from typing import final, Sequence

from .base import ASTNode, Name, Span


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

    def __init__(self, span: Span, left: Type, right: Type) -> None:
        super().__init__(span)
        self.left: Type = left
        self.right: Type = right

    def __eq__(self, other) -> bool:
        if isinstance(other, FuncType):
            return self.left == other.left and self.right == other.right
        return NotImplemented

    __hash__ = object.__hash__


class GenericType(Type):

    __slots__ = ("args", "base", "span", "type_")

    def __init__(self, span: Span, base: Name, args: Sequence[Type] = ()) -> None:
        super().__init__(span)
        self.base: Name = base
        self.args: Sequence[Type] = args

    @classmethod
    def tuple_type(cls, span: Span, args: Sequence[Type]):
        return cls(span, Name(span, "tuple"), args)

    @classmethod
    def unit(cls, span):
        return cls(span, Name(span, "Unit"))

    def __eq__(self, other):
        if isinstance(other, GenericType):
            return self.base == other.base and tuple(self.args) == tuple(other.args)
        return NotImplemented

    __hash__ = object.__hash__


class TypeScheme(Type):
    __slots__ = ("actual_type", "bound_type", "span", "type_")

    def __init__(self, actual_type: Type, bound_types: set["TypeVar"]) -> None:
        super().__init__(actual_type.span)
        self.actual_type: Type = actual_type
        self.bound_types: set[TypeVar] = bound_types

    def __eq__(self, other) -> bool:
        if isinstance(other, TypeScheme):
            return (
                self.actual_type == other.actual_type
                and self.bound_types == other.bound_types
            )
        return NotImplemented

    def fold(self) -> "TypeScheme":
        """Merge several nested type schemes into a single one."""
        if isinstance(self.actual_type, TypeScheme):
            inner = self.actual_type.fold()
            return TypeScheme(inner.actual_type, inner.bound_types | self.bound_types)
        return self

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
        if isinstance(other, TypeVar):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

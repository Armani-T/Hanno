from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from . import base, lowered, typed
from .types_ import Type

_BaseReturnType = TypeVar("_BaseReturnType", covariant=True)
_TypedReturnType = TypeVar("_TypedReturnType", covariant=True)
_LoweredReturnType = TypeVar("_LoweredReturnType", covariant=True)


class BaseASTVisitor(Generic[_BaseReturnType], ABC):
    """
    The base class for the AST visitors that operate on the base
    AST nodes kept in `asts.base`.
    """

    def run(self, node: base.ASTNode) -> _BaseReturnType:
        """
        Run this visitor on the entire tree as if `node` is the root of
        the entire AST.

        Parameters
        ----------
        node: base.ASTNode
            The (assumed) root node for the entire AST.
        """
        return node.visit(self)

    @abstractmethod
    def visit_annotation(self, node: base.Annotation) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_apply(self, node: base.Apply) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_block(self, node: base.Block) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_cond(self, node: base.Cond) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_define(self, node: base.Define) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_function(self, node: base.Function) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_impl(self, node: base.Impl) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_list(self, node: base.List) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_match(self, node: base.Match) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_pair(self, node: base.Pair) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_pattern(self, node: base.Pattern) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_name(self, node: base.Name) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_scalar(self, node: base.Scalar) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_trait(self, node: base.Trait) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_type(self, node: Type) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_unit(self, node: base.Unit) -> _BaseReturnType:
        ...


class TypedASTVisitor(Generic[_TypedReturnType], ABC):
    """
    The base class for the AST visitors that operate on the typed
    AST nodes kept in `asts.typed`.
    """

    def run(self, node: base.ASTNode) -> _BaseReturnType:
        """
        Run this visitor on the entire tree as if `node` is the root of
        the entire AST.

        Parameters
        ----------
        node: typed.ASTNode
            The (assumed) root node for the entire AST.
        """
        return node.visit(self)

    @abstractmethod
    def visit_apply(self, node: base.Apply) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_block(self, node: typed.Block) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_cond(self, node: typed.Cond) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_define(self, node: typed.Define) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_function(self, node: typed.Function) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_impl(self, node: typed.Impl) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_list(self, node: typed.List) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_match(self, node: typed.Match) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_pair(self, node: typed.Pair) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_name(self, node: typed.Name) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_scalar(self, node: typed.Scalar) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_trait(self, node: typed.Trait) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_type(self, node: Type) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_unit(self, node: typed.Unit) -> _TypedReturnType:
        ...


class LoweredASTVisitor(Generic[_LoweredReturnType], ABC):
    """
    The base class for the AST visitors that operate on the lowered
    AST nodes kept in `asts.lowered`.
    """

    def run(self, node: lowered.LoweredASTNode) -> _LoweredReturnType:
        """
        Run this visitor on the entire tree as if `node` is the root of
        the entire AST.

        Parameters
        ----------
        node: lowered.ASTNode
            The (assumed) root node for the entire AST.
        """
        return node.visit(self)

    @abstractmethod
    def visit_apply(self, node: lowered.Apply) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_block(self, node: lowered.Block) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_cond(self, node: lowered.Cond) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_define(self, node: lowered.Define) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_function(self, node: lowered.Function) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_list(self, node: lowered.List) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_pair(self, node: lowered.Pair) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_name(self, node: lowered.Name) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_native_op(self, node: lowered.NativeOp) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_scalar(self, node: lowered.Scalar) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_unit(self, node: lowered.Unit) -> _LoweredReturnType:
        ...

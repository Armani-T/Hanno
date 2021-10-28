# pylint: disable=C0115
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from . import base, lowered, typed
from .types import Type

_BaseReturnType = TypeVar("_BaseReturnType", covariant=True)
_TypedReturnType = TypeVar("_TypedReturnType", covariant=True)
_LoweredReturnType = TypeVar("_LoweredReturnType", covariant=True)


class BaseASTVisitor(Generic[_BaseReturnType], ABC):
    """
    The base class for the AST transformers that operate on the base
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
    def visit_block(self, node: base.Block) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_cond(self, node: base.Cond) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_define(self, node: base.Define) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_func_call(self, node: base.FuncCall) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_function(self, node: base.Function) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_name(self, node: base.Name) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_scalar(self, node: base.Scalar) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_type(self, node: Type) -> _BaseReturnType:
        ...

    @abstractmethod
    def visit_vector(self, node: base.Vector) -> _BaseReturnType:
        ...


class TypedASTVisitor(Generic[_TypedReturnType], ABC):
    """
    The base class for the AST transformers that operate on the typed
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
    def visit_block(self, node: typed.Block) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_cond(self, node: typed.Cond) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_define(self, node: typed.Define) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_func_call(self, node: typed.FuncCall) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_function(self, node: typed.Function) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_name(self, node: typed.Name) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_scalar(self, node: typed.Scalar) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_type(self, node: Type) -> _TypedReturnType:
        ...

    @abstractmethod
    def visit_vector(self, node: typed.Vector) -> _TypedReturnType:
        ...


class LoweredASTVisitor(Generic[_LoweredReturnType], ABC):
    """
    The base class for the AST transformers that operate on the lowered
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
    def visit_block(self, node: lowered.Block) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_cond(self, node: lowered.Cond) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_define(self, node: lowered.Define) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_func_call(self, node: lowered.FuncCall) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_function(self, node: lowered.Function) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_name(self, node: lowered.Name) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_native_operation(
        self, node: lowered.NativeOperation
    ) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_scalar(self, node: lowered.Scalar) -> _LoweredReturnType:
        ...

    @abstractmethod
    def visit_vector(self, node: lowered.Vector) -> _LoweredReturnType:
        ...

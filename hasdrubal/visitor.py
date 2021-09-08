from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from asts import base, typed
from asts.types import Type

_BaseReturnType = TypeVar("_BaseReturnType", covariant=True)
_TypedReturnType = TypeVar("_TypedReturnType", covariant=True)


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

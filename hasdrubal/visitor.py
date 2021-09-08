from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from asts import base
from asts.types import Type

_BaseReturnType = TypeVar("_BaseReturnType", covariant=True)


class BaseASTVisitor(Generic[_BaseReturnType], ABC):
    """
    The base class for the AST transformers that operate on the base
    AST nodes kept in `asts.base`.
    """

    def run(self, node: base.ASTNode) -> _BaseReturnType:
        """
        This function runs the visitor on the entire tree so the
        `node` given should be the root of the whole tree. What it
        returns depends on the  specific subclass.

        Parameters
        ----------
        node: base.ASTNode
            The root node of the tree.
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

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from asts import base as ast
from asts.types import Type

ReturnType = TypeVar("ReturnType", covariant=True)


class NodeVisitor(Generic[ReturnType], ABC):
    """
    This is the base class that defines all the AST transformers
    which will each be encoded as a compiler pass.
    """

    def run(self, node: ast.ASTNode) -> ReturnType:
        """
        This function runs the visitor on the entire tree so the
        `node` given should be the root of the whole tree. What it
        returns depends on the  specific subclass.

        Parameters
        ----------
        node: ast.ASTNode
            The root node of the tree.
        """
        return node.visit(self)

    @abstractmethod
    def visit_block(self, node: ast.Block) -> ReturnType:
        ...

    @abstractmethod
    def visit_cond(self, node: ast.Cond) -> ReturnType:
        ...

    @abstractmethod
    def visit_define(self, node: ast.Define) -> ReturnType:
        ...

    @abstractmethod
    def visit_func_call(self, node: ast.FuncCall) -> ReturnType:
        ...

    @abstractmethod
    def visit_function(self, node: ast.Function) -> ReturnType:
        ...

    @abstractmethod
    def visit_name(self, node: ast.Name) -> ReturnType:
        ...

    @abstractmethod
    def visit_scalar(self, node: ast.Scalar) -> ReturnType:
        ...

    @abstractmethod
    def visit_type(self, node: Type) -> ReturnType:
        ...

    @abstractmethod
    def visit_vector(self, node: ast.Vector) -> ReturnType:
        ...

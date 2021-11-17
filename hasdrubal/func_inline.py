from typing import Container, List, Mapping, Set

from asts.types_ import Type
from asts import base, visitor


class _Scorer(visitor.BaseASTVisitor[int]):
    """
    A visitor that gives a numeric weight to a piece of the AST.

    This visitor gives more weight to more complex structures like
    conditionals compared to simple names.
    """

    def visit_block(self, node: base.Block) -> int:
        return 2 + sum(expr.visit(self) for expr in node.body)

    def visit_cond(self, node: base.Cond) -> int:
        return (
            3 + node.pred.visit(self) + node.cons.visit(self) + node.else_.visit(self)
        )

    def visit_define(self, node: base.Define) -> int:
        return 2 + node.value.visit(self)

    def visit_func_call(self, node: base.FuncCall) -> int:
        return node.caller.visit(self) + node.callee.visit(self)

    def visit_function(self, node: base.Function) -> int:
        return 5 + node.body.visit(self)

    def visit_name(self, node: base.Name) -> int:
        return 1

    def visit_scalar(self, node: base.Scalar) -> int:
        return 1

    def visit_type(self, node: Type) -> int:
        return 0

    def visit_vector(self, node: base.Vector) -> int:
        type_weight = 2 if node.vec_type == base.VectorTypes.LIST else 1
        return type_weight + sum(elem.visit(self) for elem in node.elements)


class _Finder(visitor.BaseASTVisitor[None]):
    def __init__(self) -> None:
        self.funcs: List[base.Function] = []
        self.defined_funcs: Set[base.Function] = set()

    def visit_block(self, node: base.Block) -> None:
        for expr in node.body:
            expr.visit(self)

    def visit_cond(self, node: base.Cond) -> None:
        node.pred.visit(self)
        node.cons.visit(self)
        node.else_.visit(self)

    def visit_define(self, node: base.Define) -> None:
        node.value.visit(self)
        if isinstance(node.value, base.Function):
            self.defined_funcs.add(node.value)

    def visit_func_call(self, node: base.FuncCall) -> None:
        node.caller.visit(self)
        node.callee.visit(self)

    def visit_function(self, node: base.Function) -> None:
        node.body.visit(self)
        self.funcs.append(node)

    def visit_name(self, node: base.Name) -> None:
        return

    def visit_scalar(self, node: base.Scalar) -> None:
        return

    def visit_type(self, node: Type) -> None:
        return

    def visit_vector(self, node: base.Vector) -> None:
        for elem in node.elements:
            elem.visit(self)

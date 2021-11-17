from typing import Container, List, Mapping, Sequence, Set

from asts.types_ import Type
from asts import base, visitor
from scope import Scope


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


class _Inliner(visitor.BaseASTVisitor[base.ASTNode]):
    def __init__(
        self, scores: Mapping[base.Function, int], threshold: int = 25
    ) -> None:
        self.current_scope: Scope[base.Function] = Scope(None)
        self.scores: Mapping[base.Function, int] = {
            func: score for func, score in scores if score <= threshold
        }

    def visit_block(self, node: base.Block) -> base.Block:
        return base.Block(node.span, [expr.visit(self) for expr in node.body])

    def visit_cond(self, node: base.Cond) -> base.Cond:
        return base.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> base.Define:
        value = node.value.visit(self)
        if isinstance(value, base.Function):
            self.current_scope[node.target] = value
        return base.Define(node.span, node.target, value)

    def visit_func_call(self, node: base.FuncCall) -> base.FuncCall:
        raise NotImplementedError

    def visit_function(self, node: base.Function) -> base.Function:
        return base.Function(node.span, node.param, node.body.visit(self))

    def visit_name(self, node: base.Name) -> base.Name:
        return node

    def visit_scalar(self, node: base.Scalar) -> base.Scalar:
        return node

    def visit_type(self, node: Type) -> Type:
        return node

    def visit_vector(self, node: base.Vector) -> base.Vector:
        return base.Vector(
            node.span, node.vec_type, [elem.visit(self) for elem in node.elements]
        )


def generate_scores(
    funcs: Sequence[base.Function], defined_funcs: Container[base.Function]
) -> Mapping[base.Function, int]:
    """
    Generate the total inlining score for every function found in the
    AST.

    Parameters
    ----------
    funcs: Sequence[base.Function]
        All the `Function` nodes found in the AST.
    defined_funcs: Container[base.Function]
        A set of functions that are directly tied to a `Define` node.

    Returns
    -------
    Mapping[base.Function, int]
        A mapping between each of those function nodes and their
        overall scores.
    """
    scorer = _Scorer()
    return {
        func: (scorer.run(func) + (1 if func in defined_funcs else 3)) for func in funcs
    }

from typing import Container, List, Mapping, Sequence, Set, Tuple

from asts.types_ import Type
from asts import base, visitor
from scope import Scope


def inline_functions(tree: base.ASTNode, threshold: int = 25) -> base.ASTNode:
    """
    Inline unnecessary or trivial functions to make the program run faster.

    Parameters
    ----------
    tree: base.ASTNode
        The tree without any inlined functions.
    threshold: int
        The number that determines how aggressive the inlining should
        be. (default: 25)

    Returns
    -------
    base.ASTNode
        The tree with as many functions inlines as is reasonable.
    """
    finder = _Finder()
    finder.run(tree)
    scores = generate_scores(finder.funcs, finder.defined_funcs)
    inliner = _Inliner(scores, threshold)
    return inliner.run(tree)


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
    def __init__(self, scores: Mapping[base.Function, int], threshold: int) -> None:
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

    def visit_func_call(self, node: base.FuncCall) -> base.ASTNode:
        caller, callee = node.caller.visit(self), node.callee.visit(self)
        if isinstance(caller, base.Name) and caller in self.current_scope:
            actual_function = self.current_scope[caller]
            return inline(node.span, actual_function, callee)
        if isinstance(caller, base.Function) and caller in self.scores:
            return inline(node.span, caller, callee)
        return base.FuncCall(node.span, caller, callee)

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


class _Replacer(visitor.BaseASTVisitor[base.ASTNode]):
    def __init__(self, name: base.Name, value: base.ASTNode) -> None:
        self.name: base.Name = name
        self.value: base.ASTNode = value

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
        return base.Define(node.span, node.target, node.value.visit(self))

    def visit_func_call(self, node: base.FuncCall) -> base.ASTNode:
        return base.FuncCall(
            node.span, node.caller.visit(self), node.callee.visit(self)
        )

    def visit_function(self, node: base.Function) -> base.Function:
        return base.Function(node.span, node.param, node.body.visit(self))

    def visit_name(self, node: base.Name) -> base.ASTNode:
        return self.value if node == self.name else node

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


def inline(
    span: Tuple[int, int], func: base.Function, arg: base.ASTNode
) -> base.ASTNode:
    """Merge a function and its argument to produce an expression."""
    replacer = _Replacer(func.param, arg)
    result = replacer.run(func.body)
    result.span = span
    return result

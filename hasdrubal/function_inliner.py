from typing import Container, List, Mapping, Sequence, Set, Tuple

from asts.base import VectorTypes
from asts import lowered, visitor
from scope import Scope


def inline_functions(
    tree: lowered.LoweredASTNode, threshold: int = 25
) -> lowered.LoweredASTNode:
    """
    Inline unnecessary or trivial functions to make the program run faster.

    Parameters
    ----------
    tree: lowered.LoweredASTNode
        The tree without any inlined functions.
    threshold: int
        The number that determines how aggressive the inlining should
        be. (default: 25)

    Returns
    -------
    lowered.LoweredASTNode
        The tree with as many functions inlines as is reasonable.
    """
    finder = _Finder()
    finder.run(tree)
    scores = generate_scores(finder.funcs, finder.defined_funcs)
    inliner = _Inliner(scores, threshold)
    return inliner.run(tree)


class _Scorer(visitor.LoweredASTVisitor[int]):
    """
    A visitor that gives a numeric weight to a piece of the AST.

    This visitor gives more weight to more complex structures like
    conditionals compared to simple names.
    """

    def visit_block(self, node: lowered.Block) -> int:
        return 2 + sum(expr.visit(self) for expr in node.body)

    def visit_cond(self, node: lowered.Cond) -> int:
        return (
            3 + node.pred.visit(self) + node.cons.visit(self) + node.else_.visit(self)
        )

    def visit_define(self, node: lowered.Define) -> int:
        return 2 + node.value.visit(self)

    def visit_func_call(self, node: lowered.FuncCall) -> int:
        return node.func.visit(self) + sum(map(self.run, node.args))

    def visit_function(self, node: lowered.Function) -> int:
        return 5 + node.body.visit(self)

    def visit_name(self, node: lowered.Name) -> int:
        return 1

    def visit_native_operation(self, node: lowered.NativeOperation) -> int:
        return (
            1
            + node.left.visit(self)
            + (0 if node.right is None else node.right.visit(self))
        )

    def visit_scalar(self, node: lowered.Scalar) -> int:
        return 1

    def visit_vector(self, node: lowered.Vector) -> int:
        type_weight = 2 if node.vec_type == VectorTypes.LIST else 1
        return type_weight + sum(elem.visit(self) for elem in node.elements)


class _Finder(visitor.LoweredASTVisitor[None]):
    def __init__(self) -> None:
        self.funcs: List[lowered.Function] = []
        self.defined_funcs: Set[lowered.Function] = set()

    def visit_block(self, node: lowered.Block) -> None:
        for expr in node.body:
            expr.visit(self)

    def visit_cond(self, node: lowered.Cond) -> None:
        node.pred.visit(self)
        node.cons.visit(self)
        node.else_.visit(self)

    def visit_define(self, node: lowered.Define) -> None:
        node.value.visit(self)
        if isinstance(node.value, lowered.Function):
            self.defined_funcs.add(node.value)

    def visit_func_call(self, node: lowered.FuncCall) -> None:
        node.func.visit(self)
        for arg in node.args:
            arg.visit(self)

    def visit_function(self, node: lowered.Function) -> None:
        node.body.visit(self)
        self.funcs.append(node)

    def visit_name(self, node: lowered.Name) -> None:
        return

    def visit_native_operation(self, node: lowered.NativeOperation) -> None:
        node.left.visit(self)
        if node.right is not None:
            node.right.visit(self)

    def visit_scalar(self, node: lowered.Scalar) -> None:
        return

    def visit_vector(self, node: lowered.Vector) -> None:
        for elem in node.elements:
            elem.visit(self)


class _Inliner(visitor.LoweredASTVisitor[lowered.LoweredASTNode]):
    def __init__(self, scores: Mapping[lowered.Function, int], threshold: int) -> None:
        self.current_scope: Scope[lowered.Function] = Scope(None)
        self.scores: Mapping[lowered.Function, int] = {
            func: score for func, score in scores.items() if score <= threshold
        }

    def visit_block(self, node: lowered.Block) -> lowered.Block:
        return lowered.Block(node.span, [expr.visit(self) for expr in node.body])

    def visit_cond(self, node: lowered.Cond) -> lowered.Cond:
        return lowered.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: lowered.Define) -> lowered.Define:
        value = node.value.visit(self)
        if isinstance(value, lowered.Function):
            self.current_scope[node.target] = value
        return lowered.Define(node.span, node.target, value)

    def visit_func_call(self, node: lowered.FuncCall) -> lowered.LoweredASTNode:
        func = node.func.visit(self)
        args = [arg.visit(self) for arg in node.args]
        if isinstance(func, lowered.Name) and func in self.current_scope:
            actual_function = self.current_scope[func]
            return inline(node.span, actual_function, args)
        if isinstance(func, lowered.Function) and func in self.scores:
            return inline(node.span, func, args)
        return lowered.FuncCall(node.span, func, args)

    def visit_function(self, node: lowered.Function) -> lowered.Function:
        return lowered.Function(node.span, node.params, node.body.visit(self))

    def visit_name(self, node: lowered.Name) -> lowered.Name:
        return node

    def visit_native_operation(
        self, node: lowered.NativeOperation
    ) -> lowered.NativeOperation:
        return lowered.NativeOperation(
            node.span,
            node.operation,
            node.left.visit(self),
            None if node.right is None else node.right.visit(self),
        )

    def visit_scalar(self, node: lowered.Scalar) -> lowered.Scalar:
        return node

    def visit_vector(self, node: lowered.Vector) -> lowered.Vector:
        return lowered.Vector(
            node.span, node.vec_type, [elem.visit(self) for elem in node.elements]
        )


class _Replacer(visitor.LoweredASTVisitor[lowered.LoweredASTNode]):
    def __init__(self, inlined: Scope[lowered.LoweredASTNode]) -> None:
        self.inlined: Scope[lowered.LoweredASTNode] = inlined

    def visit_block(self, node: lowered.Block) -> lowered.Block:
        return lowered.Block(node.span, [expr.visit(self) for expr in node.body])

    def visit_cond(self, node: lowered.Cond) -> lowered.Cond:
        return lowered.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: lowered.Define) -> lowered.Define:
        return lowered.Define(node.span, node.target, node.value.visit(self))

    def visit_func_call(self, node: lowered.FuncCall) -> lowered.LoweredASTNode:
        return lowered.FuncCall(
            node.span,
            node.func.visit(self),
            [arg.visit(self) for arg in node.args],
        )

    def visit_function(self, node: lowered.Function) -> lowered.Function:
        return lowered.Function(node.span, node.params, node.body.visit(self))

    def visit_name(self, node: lowered.Name) -> lowered.LoweredASTNode:
        return self.inlined[node] if node in self.inlined else node

    def visit_native_operation(
        self, node: lowered.NativeOperation
    ) -> lowered.NativeOperation:
        return lowered.NativeOperation(
            node.span,
            node.operation,
            node.left.visit(self),
            None if node.right is None else node.right.visit(self),
        )

    def visit_scalar(self, node: lowered.Scalar) -> lowered.Scalar:
        return node

    def visit_vector(self, node: lowered.Vector) -> lowered.Vector:
        return lowered.Vector(
            node.span, node.vec_type, [elem.visit(self) for elem in node.elements]
        )


def generate_scores(
    funcs: Sequence[lowered.Function], defined_funcs: Container[lowered.Function]
) -> Mapping[lowered.Function, int]:
    """
    Generate the total inlining score for every function found in the
    AST.

    Parameters
    ----------
    funcs: Sequence[lowered.Function]
        All the `Function` nodes found in the AST.
    defined_funcs: Container[lowered.Function]
        A set of functions that are directly tied to a `Define` node.

    Returns
    -------
    Mapping[lowered.Function, int]
        A mapping between each of those function nodes and their
        overall scores.
    """
    scorer = _Scorer()
    return {
        func: (scorer.run(func) + (1 if func in defined_funcs else 3)) for func in funcs
    }


def inline(
    span: Tuple[int, int],
    func: lowered.Function,
    args: Sequence[lowered.LoweredASTNode],
) -> lowered.LoweredASTNode:
    """Merge a function and its argument to produce an expression."""
    inlined = {param.value: arg for param, arg in zip(func.params, args)}
    replacer = _Replacer(Scope.from_dict(inlined))
    result = replacer.run(func.body)
    result.span = span
    return result

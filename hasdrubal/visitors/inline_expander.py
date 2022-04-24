# TODO: Ensure that functions marked for inlining aren't recursive to
#  prevent infinite loops.
from typing import Collection, List, Sequence, Set

from asts import lowered, visitor
from scope import Scope

calc_threshold = lambda value: value * 20


def expand_inline(tree: lowered.LoweredASTNode, level: int) -> lowered.LoweredASTNode:
    """
    Inline unnecessary or trivial functions to make the program run faster.

    Parameters
    ----------
    tree: lowered.LoweredASTNode
        The tree without any inlined functions.
    level: int
        How aggressive the inline expander should be in optimising.

    Returns
    -------
    lowered.LoweredASTNode
        The tree with as many functions inlines as is reasonable.
    """
    level = calc_threshold(level)
    finder = _Finder()
    finder.run(tree)
    targets = generate_targets(finder.funcs, finder.defined_funcs, level)
    inliner = _Inliner(targets)
    return inliner.run(tree)


class _Scorer(visitor.LoweredASTVisitor[int]):
    """
    A visitor that gives a numeric weight to a piece of the AST.

    This visitor gives more weight to more complex structures like
    conditionals compared to simple names.
    """

    def visit_apply(self, node: lowered.Apply) -> int:
        return 2 + node.func.visit(self) + node.arg.visit(self)

    def visit_block(self, node: lowered.Block) -> int:
        return 5 + sum(expr.visit(self) for expr in node.body)

    def visit_cond(self, node: lowered.Cond) -> int:
        return (
            6 + node.pred.visit(self) + node.cons.visit(self) + node.else_.visit(self)
        )

    def visit_define(self, node: lowered.Define) -> int:
        return 4 + node.value.visit(self)

    def visit_function(self, node: lowered.Function) -> int:
        return 7 + node.body.visit(self)

    def visit_list(self, node: lowered.List) -> int:
        element_score = sum(elem.visit(self) for elem in node.elements)
        return (3 + element_score) if element_score else 1

    def visit_pair(self, node: lowered.Pair) -> int:
        return 2 + node.first.visit(self) + node.second.visit(self)

    def visit_name(self, node: lowered.Name) -> int:
        return 0

    def visit_native_op(self, node: lowered.NativeOp) -> int:
        return (
            1
            + node.left.visit(self)
            + (0 if node.right is None else node.right.visit(self))
        )

    def visit_scalar(self, node: lowered.Scalar) -> int:
        return 0

    def visit_unit(self, node: lowered.Unit) -> int:
        return 0


class _Finder(visitor.LoweredASTVisitor[None]):
    def __init__(self) -> None:
        self.funcs: List[lowered.Function] = []
        self.defined_funcs: Set[lowered.Function] = set()

    def visit_apply(self, node: lowered.Apply) -> None:
        node.func.visit(self)
        node.arg.visit(self)

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

    def visit_function(self, node: lowered.Function) -> None:
        node.body.visit(self)
        self.funcs.append(node)

    def visit_list(self, node: lowered.List) -> None:
        for elem in node.elements:
            elem.visit(self)

    def visit_pair(self, node: lowered.Pair) -> None:
        node.first.visit(self)
        node.second.visit(self)

    def visit_name(self, node: lowered.Name) -> None:
        return

    def visit_native_op(self, node: lowered.NativeOp) -> None:
        node.left.visit(self)
        if node.right is not None:
            node.right.visit(self)

    def visit_scalar(self, node: lowered.Scalar) -> None:
        return

    def visit_unit(self, node: lowered.Unit) -> None:
        return


class _Inliner(visitor.LoweredASTVisitor[lowered.LoweredASTNode]):
    def __init__(self, targets: Collection[lowered.Function]) -> None:
        self.current_scope: Scope[lowered.Function] = Scope(None)
        self.targets: Collection[lowered.Function] = targets

    def is_target(self, node: lowered.LoweredASTNode) -> bool:
        """Check whether a function node is marked for inlining."""
        return any(node == target for target in self.targets)

    def visit_apply(self, node: lowered.Apply) -> lowered.LoweredASTNode:
        func, arg = node.func.visit(self), node.arg.visit(self)
        if self.is_target(func):
            return inline_function(func, arg)
        if isinstance(func, lowered.Name) and func in self.current_scope:
            return inline_function(self.current_scope[func], arg)
        return lowered.Apply(func, arg)

    def visit_block(self, node: lowered.Block) -> lowered.Block:
        return lowered.Block([expr.visit(self) for expr in node.body])

    def visit_cond(self, node: lowered.Cond) -> lowered.Cond:
        return lowered.Cond(
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: lowered.Define) -> lowered.Define:
        value = node.value.visit(self)
        if isinstance(value, lowered.Function):
            self.current_scope[node.target] = value
        return lowered.Define(node.target, value)

    def visit_function(self, node: lowered.Function) -> lowered.Function:
        return lowered.Function(node.param, node.body.visit(self))

    def visit_list(self, node: lowered.List) -> lowered.List:
        return lowered.List([elem.visit(self) for elem in node.elements])

    def visit_pair(self, node: lowered.Pair) -> lowered.Pair:
        return lowered.Pair(node.first.visit(self), node.second.visit(self))

    def visit_name(self, node: lowered.Name) -> lowered.Name:
        return node

    def visit_native_op(self, node: lowered.NativeOp) -> lowered.NativeOp:
        return lowered.NativeOp(
            node.operation,
            node.left.visit(self),
            None if node.right is None else node.right.visit(self),
        )

    def visit_scalar(self, node: lowered.Scalar) -> lowered.Scalar:
        return node

    def visit_unit(self, node: lowered.Unit) -> lowered.Unit:
        return node


class _Replacer(visitor.LoweredASTVisitor[lowered.LoweredASTNode]):
    def __init__(self, param: lowered.Name, arg: lowered.LoweredASTNode) -> None:
        self.inlined_param: lowered.Name = param
        self.new_value: lowered.LoweredASTNode = arg

    def visit_apply(self, node: lowered.Apply) -> lowered.LoweredASTNode:
        return lowered.Apply(
            node.func.visit(self),
            node.arg.visit(self),
        )

    def visit_block(self, node: lowered.Block) -> lowered.Block:
        return lowered.Block([expr.visit(self) for expr in node.body])

    def visit_cond(self, node: lowered.Cond) -> lowered.Cond:
        return lowered.Cond(
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: lowered.Define) -> lowered.Define:
        return lowered.Define(node.target, node.value.visit(self))

    def visit_function(self, node: lowered.Function) -> lowered.Function:
        return (
            node
            if node.param == self.inlined_param
            else lowered.Function(node.param, node.body.visit(self))
        )

    def visit_list(self, node: lowered.List) -> lowered.List:
        return lowered.List([elem.visit(self) for elem in node.elements])

    def visit_pair(self, node: lowered.Pair) -> lowered.Pair:
        return lowered.Pair(node.first.visit(self), node.second.visit(self))

    def visit_name(self, node: lowered.Name) -> lowered.LoweredASTNode:
        return self.new_value if node == self.inlined_param else node

    def visit_native_op(self, node: lowered.NativeOp) -> lowered.NativeOp:
        return lowered.NativeOp(
            node.operation,
            node.left.visit(self),
            None if node.right is None else node.right.visit(self),
        )

    def visit_scalar(self, node: lowered.Scalar) -> lowered.Scalar:
        return node

    def visit_unit(self, node: lowered.Unit) -> lowered.Unit:
        return node


def generate_targets(
    funcs: Sequence[lowered.Function],
    defined_funcs: Collection[lowered.Function],
    threshold: int = 0,
) -> Collection[lowered.Function]:
    """
    Generate the total inlining score for every function found in the
    AST.

    Parameters
    ----------
    funcs: Sequence[lowered.Function]
        All the `Function` nodes found in the AST.
    defined_funcs: Collection[lowered.Function]
        A set of functions that are directly tied to a `Define` node.
    threshold: int
        The highest score that is allowed to remain in the final result.
        If it is `0` then it will count and collect the score of every
        single function given.

    Returns
    -------
    Collection[lowered.Function]
        A list of all the function nodes whose overall score is less
        than the threshold.
    """
    allow_all = threshold == 0
    base_scorer = _Scorer()
    scores = []
    for func in funcs:
        score = base_scorer.run(func.body)
        score += 1 if func in defined_funcs else 3
        if allow_all or score <= threshold:
            scores.append(func)
    return scores


def inline_function(
    func: lowered.Function, arg: lowered.LoweredASTNode
) -> lowered.LoweredASTNode:
    """Merge a function and its argument to produce an expression."""
    replacer = _Replacer(func.param.value, arg)
    return replacer.run(func.body)

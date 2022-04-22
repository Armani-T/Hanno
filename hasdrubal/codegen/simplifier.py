from functools import reduce
from re import compile as re_compile
from typing import Sequence, Tuple, Union

from asts import base, lowered, visitor
from errors import FatalInternalError, InexhaustivePatternError, merge, PatternPosition
from log import logger

NON_BINDING_NAME_REGEX = re_compile(r"_+")
NEW_NAME_INDEX = 0
TRUE_NODE = base.Scalar((0, 0), True)

_get_length_pred = lambda span, initials_size, subject: base.Apply(
    span,
    base.Apply(
        span,
        base.Name(span, ">="),
        base.Apply(span, base.Name(span, "length"), subject),
    ),
    base.Scalar(span, initials_size),
)


def simplify(node: base.ASTNode) -> lowered.LoweredASTNode:
    """
    Convert the higher level AST into a simpler representation that's
    still an AST.

    Parameters
    ----------
    node: ASTNode
        The higher-level, more complex AST.

    Returns
    -------
    LoweredASTNode
        The simplified AST with things like `+` and `*` being
        converted to operation nodes instead of function calls.
    """
    return Simplifier().run(node)


class Simplifier(visitor.BaseASTVisitor[lowered.LoweredASTNode]):
    """
    Convert either the base AST or the typed AST into a lowered AST
    used for some optimisations and (more importantly) bytecode
    generation.
    """

    def __init__(self) -> None:
        self._param_index: int = 0

    def visit_apply(self, node: base.Apply) -> Union[lowered.Apply, lowered.NativeOp]:
        func, arg = node.func.visit(self), node.arg.visit(self)
        if func == lowered.Name("~"):
            return lowered.NativeOp(lowered.OperationTypes.NEG, arg)

        binary_ops = [op.value for op in lowered.OperationTypes]
        if (
            isinstance(func, base.Apply)
            and isinstance(func.func, base.Name)
            and func.func.value in binary_ops
        ):
            return lowered.NativeOp(
                lowered.OperationTypes(func.func.value), func.arg.visit(self), arg
            )
        return lowered.Apply(func, arg)

    def visit_block(self, node: base.Block) -> lowered.Block:
        new_exprs = []
        for base_expr in node.body:
            expr = base_expr.visit(self)
            if isinstance(expr, lowered.Block) and expr.metadata.get("merge_parent"):
                new_exprs.extend(expr.body)
            else:
                new_exprs.append(expr)

        return lowered.Block(new_exprs)

    def visit_cond(self, node: base.Cond) -> lowered.Cond:
        return lowered.Cond(
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> lowered.Block:
        decomposed = decompose_define(node.target, node.value, PatternPosition.TARGET)
        lowered_node = decomposed.visit(self)
        lowered_node.metadata["merge_parent"] = True
        return lowered_node

    def visit_function(self, node: base.Function) -> lowered.Function:
        self._param_index += 1
        param_name = f"$FuncParam_{self._param_index}"
        header = decompose_define(
            node.param, node.param, PatternPosition.PARAMETER
        ).visit(self)
        base_body = node.body.visit(self)
        if isinstance(base_body, lowered.Block):
            body = lowered.Block([*header.body, *base_body.body])
        else:
            body = lowered.Block([*header.body, base_body])
        return lowered.Function(lowered.Name(param_name), body)

    def visit_list(self, node: base.List) -> lowered.List:
        return lowered.List([elem.visit(self) for elem in node.elements])

    def visit_match(self, node: base.Match) -> lowered.LoweredASTNode:
        return to_decision_tree(node).visit(self)

    def visit_pair(self, node: base.Pair) -> lowered.Pair:
        return lowered.Pair(node.first.visit(self), node.second.visit(self))

    def visit_pattern(self, node: base.Pattern):
        logger.fatal("Tried to simplify this: %r", node)
        raise FatalInternalError()

    def visit_name(self, node: base.Name) -> lowered.Name:
        return lowered.Name(node.value)

    def visit_scalar(self, node: base.Scalar) -> lowered.Scalar:
        return lowered.Scalar(node.value)

    def visit_type(self, node):
        logger.fatal("Tried to simplify this: %r", node)
        raise FatalInternalError()

    def visit_unit(self, node: base.Unit) -> Union[lowered.Unit, lowered.List]:
        return lowered.Unit()


def decompose_define(
    pattern: base.Pattern, value: base.ASTNode, position: PatternPosition
) -> base.ASTNode:
    """
    Break down an assignment of a pattern to a value into a series of
    smaller steps.
    """
    if isinstance(pattern, base.UnitPattern):
        return value
    if isinstance(pattern, base.FreeName):
        return base.Define(
            pattern.span, base.FreeName(pattern.span, pattern.value), value
        )
    if isinstance(pattern, base.PairPattern):
        return _decompose_pair(pattern, value)
    if (
        isinstance(pattern, base.ListPattern)
        and not pattern.initial_patterns
        and pattern.rest is not None
    ):
        return base.Define(pattern.span, pattern.rest, value)
    raise InexhaustivePatternError(position, pattern)


def _decompose_pair(pattern: base.PairPattern, value: base.ASTNode) -> base.Block:
    raw_name = _new_pattern_name()
    return base.Block(
        pattern.span,
        [
            base.Define(pattern.span, base.FreeName(pattern.span, raw_name), value),
            base.Define(
                pattern.first.span,
                base.FreeName(pattern.first.span, _new_pattern_name()),
                base.Apply(
                    pattern.first.span,
                    base.Name(pattern.first.span, "first"),
                    base.Name(pattern.span, raw_name),
                ),
            ),
            base.Define(
                pattern.second.span,
                base.FreeName(pattern.second.span, _new_pattern_name()),
                base.Apply(
                    pattern.second.span,
                    base.Name(pattern.second.span, "second"),
                    base.Name(pattern.span, raw_name),
                ),
            ),
        ],
    )


def _new_pattern_name() -> str:
    global NEW_NAME_INDEX
    NEW_NAME_INDEX += 1
    return f"$MatchItem_{NEW_NAME_INDEX}"


def to_decision_tree(node: base.Match) -> base.ASTNode:
    """
    Turn a match expression into a series of `if` and `let` expressions
    that accomplish the same thing.

    Parameters
    ----------
    node: base.Match
        The match expression that is to be converted.

    Returns
    -------
    base.Block
        The series of `if` and `let` expressions.
    """
    branches = [build_branch(node.subject, pattern) for pattern, cons in node.cases]
    if not branches:
        raise ValueError(f"Encountered match expression `{node}` with 0 cases.")

    final, *branches = reversed(branches)
    final_pred, final_defs = final
    if not branches and final_pred == TRUE_NODE:
        only_cons = node.cases[0][1]
        cons = only_cons.body if isinstance(only_cons, base.Block) else [only_cons]
        return base.Block(node.span, [*final_defs, *cons])

    parts = (
        (pred_defs[0], pred_defs[1], cases[1])
        for pred_defs, cases in zip(branches, node.cases)
    )
    result: base.ASTNode = base.Block(node.span, final_defs)
    for pred, defs, cons in parts:
        rest = cons.body if isinstance(cons, base.Block) else [cons]
        real_cons = base.Block(node.span, [*defs, *rest])
        result = base.Cond(node.span, pred, real_cons, result)
    return result


def build_branch(
    subject: base.ASTNode, pattern: base.Pattern
) -> Tuple[base.ASTNode, Sequence[base.Define]]:
    if isinstance(pattern, base.UnitPattern):
        return TRUE_NODE, ()
    if isinstance(pattern, base.FreeName):
        if NON_BINDING_NAME_REGEX.match(pattern.value):
            return TRUE_NODE, (base.Define(pattern.span, pattern, subject),)
        return TRUE_NODE, ()
    if isinstance(pattern, base.ScalarPattern):
        scalar = base.Scalar(pattern.span, pattern.value)
        pred = base.Apply(
            pattern.span,
            base.Apply(pattern.span, base.Name(pattern.span, "="), scalar),
            subject,
        )
        return pred, ()
    if isinstance(pattern, base.PinnedName):
        name = base.Name(pattern.span, pattern.value)
        pred = base.Apply(
            pattern.span,
            base.Apply(pattern.span, base.Name(pattern.span, "="), name),
            subject,
        )
        return pred, ()
    if isinstance(pattern, base.PairPattern):
        first_subject = base.Apply(
            pattern.span, base.Name(pattern.span, "first"), subject
        )
        first_pred, first_defs = build_branch(first_subject, pattern.first)
        second_subject = base.Apply(
            pattern.span, base.Name(pattern.span, "second"), subject
        )
        second_pred, second_defs = build_branch(second_subject, pattern.second)
        return _ast_and(first_pred, second_pred), (*first_defs, *second_defs)
    if isinstance(pattern, base.ListPattern):
        return _build_list_pattern_branch(subject, pattern)
    raise TypeError(f"{type(pattern)} is an invalid subtype of asts.base.Pattern")


def _build_list_pattern_branch(
    subject: base.ASTNode, pattern: base.ListPattern
) -> Tuple[base.ASTNode, Sequence[base.Define]]:
    predicates = (
        [_get_length_pred(pattern.span, len(pattern.initial_patterns), subject)]
        if pattern.initial_patterns
        else []
    )
    definitions = []
    for index, sub_pattern in pattern.initial_patterns:
        span = sub_pattern.span
        element = base.Apply(
            span,
            base.Name(span, "at"),
            base.Pair(span, subject, base.Scalar(span, index)),
        )
        sub_predicates, sub_definitions = build_branch(element, sub_pattern)
        predicates += sub_predicates
        definitions += sub_definitions

    if pattern.rest is not None:
        definitions.append(
            base.Define(
                pattern.rest.span,
                pattern.rest,
                base.Apply(
                    pattern.rest.span,
                    base.Name(pattern.rest.span, "drop"),
                    base.Pair(
                        pattern.rest.span,
                        subject,
                        base.Scalar(pattern.rest.span, len(pattern.initial_patterns)),
                    ),
                ),
            )
        )
    return reduce(_ast_and, predicates), definitions


def _ast_and(left: base.ASTNode, right: base.ASTNode) -> base.ASTNode:
    span = merge(left.span, right.span)
    return base.Apply(span, base.Apply(span, base.Name(span, "and"), left), right)

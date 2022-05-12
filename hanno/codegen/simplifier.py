from functools import reduce
from typing import List, Optional, Sequence, Tuple, Union

from asts.types_ import Type
from asts import base, lowered, visitor
from errors import FatalInternalError, merge, PatternPosition, RefutablePatternError
from log import logger

BINARY_OPS = {op.value for op in lowered.OperationTypes}
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

    def visit_annotation(self, node: base.Annotation) -> lowered.Unit:
        return lowered.Unit()

    def visit_apply(self, node: base.Apply) -> Union[lowered.Apply, lowered.NativeOp]:
        func, arg = node.func.visit(self), node.arg.visit(self)
        if func == "~":
            return lowered.NativeOp(lowered.OperationTypes.NEG, arg)
        if (
            isinstance(func, lowered.Apply)
            and isinstance(func.func, lowered.Name)
            and func.func.value in BINARY_OPS
        ):
            return lowered.NativeOp(
                lowered.OperationTypes(func.func.value), func.arg, arg
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
        return lowered.Block.new(new_exprs)

    def visit_cond(self, node: base.Cond) -> lowered.Cond:
        return lowered.Cond(
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> lowered.LoweredASTNode:
        value = node.value.visit(self)
        return decompose_irrefutable(node.target, value, PatternPosition.TARGET)

    def visit_function(self, node: base.Function) -> lowered.Function:
        if isinstance(node.param, base.FreeName):
            return lowered.Function(
                lowered.Name(node.param.value), node.body.visit(self)
            )

        self._param_index += 1
        new_param = lowered.Name(f"$FuncParam_{self._param_index}")
        head = decompose_irrefutable(node.param, new_param, PatternPosition.PARAMETER)
        body = node.body.visit(self)
        if isinstance(body, lowered.Block) and isinstance(head, lowered.Block):
            return lowered.Function(
                new_param, lowered.Block.new((*head.body, *body.body))
            )
        if isinstance(body, lowered.Block):
            return lowered.Function(new_param, lowered.Block.new((head, *body.body)))
        if isinstance(head, lowered.Block):
            return lowered.Function(new_param, lowered.Block.new((*head.body, body)))
        return lowered.Function(new_param, lowered.Block.new((head, body)))

    def visit_impl(self, node: base.Impl):
        logger.fatal("Tried to simplify this: %r", node)
        raise FatalInternalError()

    def visit_list(self, node: base.List) -> lowered.List:
        return lowered.List([elem.visit(self) for elem in node.elements])

    def visit_match(self, node: base.Match) -> lowered.LoweredASTNode:
        tree = to_decision_tree(node)
        return tree.visit(self)

    def visit_pair(self, node: base.Pair) -> lowered.Pair:
        return lowered.Pair(node.first.visit(self), node.second.visit(self))

    def visit_pattern(self, node: base.Pattern):
        logger.fatal("Tried to simplify this: %r", node)
        raise FatalInternalError()

    def visit_name(self, node: base.Name) -> lowered.Name:
        return lowered.Name(node.value)

    def visit_scalar(self, node: base.Scalar) -> lowered.Scalar:
        return lowered.Scalar(node.value)

    def visit_trait(self, node: base.Trait):
        logger.fatal("Tried to simplify this: %r", node)
        raise FatalInternalError()

    def visit_type(self, node: Type):
        logger.fatal("Tried to simplify this: %r", node)
        raise FatalInternalError()

    def visit_unit(self, node: base.Unit) -> lowered.Unit:
        return lowered.Unit()


def decompose_irrefutable(
    pattern: base.Pattern, value: lowered.LoweredASTNode, position: PatternPosition
) -> lowered.LoweredASTNode:
    """
    Break down an assignment of a pattern to a value into a series of
    smaller steps.
    """
    if isinstance(pattern, base.UnitPattern):
        return value
    if isinstance(pattern, base.FreeName):
        return (
            value
            if pattern.value == "_"
            else lowered.Define(lowered.Name(pattern.value), value)
        )
    if isinstance(pattern, base.PairPattern):
        return _decompose_pair(pattern, value, position)
    if (
        isinstance(pattern, base.ListPattern)
        and not pattern.initial_patterns
        and pattern.rest is not None
    ):
        return lowered.Define(lowered.Name(pattern.rest.value), value)
    raise RefutablePatternError(position, pattern)


def _decompose_pair(
    pattern: base.PairPattern, value: lowered.LoweredASTNode, position: PatternPosition
) -> lowered.Block:
    first = decompose_irrefutable(
        pattern.first, lowered.Apply(lowered.Name("first"), value), position
    )
    second = decompose_irrefutable(
        pattern.second, lowered.Apply(lowered.Name("second"), value), position
    )
    result = lowered.Block.new(
        [*first.body, *second.body]
        if isinstance(first, lowered.Block) and isinstance(second, lowered.Block)
        else [*first.body, second]
        if isinstance(first, lowered.Block)
        else [first, *second.body]
        if isinstance(second, lowered.Block)
        else [first, second]
    )
    result.metadata["merge_parent"] = True
    return result


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
    branches = []
    for pattern, cons in node.cases:
        pred, defs = build_branch(node.subject, pattern)
        cons_ = cons.body if isinstance(cons, base.Block) else [cons]
        then = base.Block.new(node.span, [*defs, *cons_])
        pred = reduce_pred(pred)
        if pred is None:
            return reduce(
                lambda else_, pred_then: base.Cond(
                    pred_then[0].span, pred_then[0], pred_then[1], else_
                ),
                reversed(branches),
                then,
            )
        branches.append((pred, then))

    _, default_case = branches.pop()
    return reduce(
        lambda else_, pred_then: base.Cond(
            pred_then[0].span, pred_then[0], pred_then[1], else_
        ),
        reversed(branches),
        default_case,
    )


def build_branch(
    subject: base.ASTNode, pattern: base.Pattern
) -> Tuple[base.ASTNode, Sequence[base.Define]]:
    """
    Create a single branch of a decision tree using a pattern and the
    subject from a match expression.

    Parameters
    ----------
    subject: base.ASTNode
        The value that the pattern is matching against.
    pattern: base.Pattern
        An predicate that can be used to deconstruct a value.

    Returns
    -------
    Tuple[base.ASTNode, Sequence[base.Define]]
        A series of predicates that are equivalent to the original
        pattern and a list names that have been bound within the
        pattern.
    """
    if isinstance(pattern, base.UnitPattern):
        return TRUE_NODE, ()
    if isinstance(pattern, base.FreeName):
        return (
            TRUE_NODE,
            ()
            if pattern.value == "_"
            else (base.Define(pattern.span, pattern, subject),),
        )
    if isinstance(pattern, base.ScalarPattern):
        if isinstance(pattern.value, bool):
            pred = (
                subject
                if pattern.value
                else base.Apply(pattern.span, base.Name(pattern.span, "not"), subject)
            )
        else:
            pred = base.Apply(
                pattern.span,
                base.Apply(
                    pattern.span,
                    base.Name(pattern.span, "="),
                    base.Scalar(pattern.span, pattern.value),
                ),
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
    if not pattern.initial_patterns and pattern.rest is None:
        return (
            base.Apply(
                pattern.span,
                base.Apply(
                    pattern.span,
                    base.Name(pattern.span, "="),
                    base.Apply(
                        pattern.span, base.Name(pattern.span, "length"), subject
                    ),
                ),
                base.Scalar(pattern.span, 0),
            ),
            (),
        )

    predicates: List[base.ASTNode] = (
        [_get_length_pred(pattern.span, len(pattern.initial_patterns), subject)]
        if pattern.initial_patterns
        else []
    )
    definitions = []
    for index, sub_pattern in enumerate(pattern.initial_patterns):
        span = sub_pattern.span
        element = base.Apply(
            span,
            base.Name(span, "at"),
            base.Pair(span, subject, base.Scalar(span, index)),
        )
        sub_predicates, sub_definitions = build_branch(element, sub_pattern)
        predicates.append(sub_predicates)
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
    return reduce(_ast_and, predicates, lowered.Scalar(True)), definitions


def _ast_and(left: base.ASTNode, right: base.ASTNode) -> base.ASTNode:
    span = merge(left.span, right.span)
    return base.Apply(span, base.Apply(span, base.Name(span, "and"), left), right)


def reduce_pred(pred: base.ASTNode) -> Optional[base.ASTNode]:
    """
    Simplify a predicate by removing any obvious or constant
    expressions.

    Parameters
    ----------
    pred: base.ASTNode
        The predicate that we are supposed to simplify.

    Returns
    -------
    Optional[base.ASTNode]
        A `None` means that this branch of the decision tree should be
        left out of the final result. A `base.ASTNode` is the
        simplified predicate.
    """
    # base.Apply(span, base.Apply(span, base.Name(span, "and"), left), right)
    if pred == TRUE_NODE:
        return None
    if isinstance(pred, base.Apply) and isinstance(pred.func, base.Apply):
        return (
            reduce_pred(pred.func.arg) and reduce_pred(pred.arg)
            if pred.func.func == base.Name((0, 0), "and")
            else reduce_pred(pred.func.arg) or reduce_pred(pred.arg)
            if pred.func.func == base.Name((0, 0), "or")
            else pred
        )
    return pred

from typing import Optional

from asts import base, typed, visitors, types_ as types
from errors import InexhaustivePatternError, PatternPosition


class ExhaustivenessChecker(visitors.TypedASTVisitor[None]):
    """
    Check whether the patterns used in the code are exhaustive to
    prevent partial functions from being defined.
    """

    def visit_apply(self, node: typed.Apply) -> None:
        node.func.visit(self)
        node.arg.visit(self)

    def visit_block(self, node: typed.Block) -> None:
        for expr in node.body:
            expr.visit(self)

    def visit_cond(self, node: typed.Cond) -> None:
        node.pred.visit(self)

    def visit_define(self, node: typed.Define) -> None:
        offender = non_exhaustive(node.target)
        if offender is not None:
            raise InexhaustivePatternError(PatternPosition.TARGET, offender)
        node.value.visit(self)

    def visit_function(self, node: typed.Function) -> None:
        offender = non_exhaustive(node.param)
        if offender is not None:
            raise InexhaustivePatternError(PatternPosition.PARAMETER, offender)
        node.body.visit(self)

    def visit_list(self, node: typed.List) -> None:
        for elem in node.elements:
            elem.visit(self)

    def visit_match(self, node: typed.Match) -> None:
        node.subject.visit(self)
        offender: Optional[base.Pattern] = None
        for pattern, cons in node.cases:
            cons.visit(self)
            if (result := non_exhaustive(pattern)) is not None:
                offender = result

        if offender is not None:
            raise InexhaustivePatternError(PatternPosition.CASE, offender)

    def visit_pair(self, node: typed.Pair) -> None:
        node.first.visit(self)
        node.second.visit(self)

    def visit_name(self, node: typed.Name) -> None:
        return

    def visit_scalar(self, node: typed.Scalar) -> None:
        return

    def visit_type(self, node: types.Type) -> None:
        return

    def visit_unit(self, node: typed.Unit) -> None:
        return


def non_exhaustive(pattern: base.Pattern) -> Optional[base.Pattern]:
    """
    Check whether a pattern will always capture or whether it can fail.
    If it can fail, return the part of it that is capable fo failure.

    Parameters
    ----------
    pattern: base.Pattern
        The pattern being checked.

    Returns
    -------
    Optional[base.Pattern]
        If it's `None`, then `pattern` cannot fail. If it is not `None`,
        then it returns the part of `pattern` that can fail.
    """
    if isinstance(pattern, (base.FreeName, base.UnitPattern)):
        return None
    if isinstance(pattern, base.PairPattern):
        return non_exhaustive(pattern.first) and non_exhaustive(pattern.second)
    if (
        isinstance(pattern, base.ListPattern)
        and pattern.initial_patterns
        or pattern.rest is None
    ):
        return None
    return pattern

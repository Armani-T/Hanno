from typing import Optional

from asts import base, typed, visitors, types_ as types
from errors import PatternPosition, RefutablePatternError

_is_list = lambda node_type: (
    isinstance(node_type, types.TypeApply)
    and node_type.caller == types.TypeName((0, 0), "List")
)


def check_exhaustiveness(node: typed.TypedASTNode) -> None:
    """
    Ensure that the pattern matches in `node` are total, rather than
    partial.

    Parameters
    ----------
    node: typed.TypedASTNode
        The node that will be checked.

    Raises
    ------
    errors.RefutablePatternError
        The error raised when a non-total pattern match is found.
    """
    checker = ExhaustivenessChecker()
    checker.run(node)


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
        if (offender := non_exhaustive(node.target)) is not None:
            raise RefutablePatternError(PatternPosition.TARGET, offender)
        node.value.visit(self)

    def visit_function(self, node: typed.Function) -> None:
        if (offender := non_exhaustive(node.param)) is not None:
            raise RefutablePatternError(PatternPosition.PARAMETER, offender)
        node.body.visit(self)

    def visit_list(self, node: typed.List) -> None:
        for elem in node.elements:
            elem.visit(self)

    def visit_match(self, node: typed.Match) -> None:
        node.subject.visit(self)
        if not node.cases and node.subject.type_ != types.TypeName.never(node.span):
            raise RefutablePatternError.empty_match(node.span)

        is_exhaustive([pattern for pattern, _ in node.cases])
        for _, cons in node.cases:
            cons.visit(self)

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
    If it can fail, return the part that is capable of failure.

    Parameters
    ----------
    pattern: base.Pattern
        The pattern being checked.

    Returns
    -------
    Optional[base.Pattern]
        If it's `None`, then `pattern` cannot fail. If it isn't `None`,
        then it returns the smallest non-exhaustive section found from
        the pattern.
    """
    if isinstance(pattern, (base.FreeName, base.UnitPattern)):
        return None
    if isinstance(pattern, base.PairPattern):
        return non_exhaustive(pattern.first) or non_exhaustive(pattern.second)
    if (
        isinstance(pattern, base.ListPattern)
        and not pattern.initial_patterns
        and pattern.rest is not None
    ):
        return None
    return pattern


def is_exhaustive(patterns: list[base.Pattern]) -> None:
    """
    Check if a group of patterns are exhaustive. If not, raise a
    `RefutablePatternError`.

    Parameters
    ----------
    patterns: list[base.Pattern]
        A list of patterns from a match expr to check if it matches
        all possible options.

    Returns
    -------
    None
        This function returns nothing if the patterns are exhaustive.
        If they aren'tm it will raise a `RefutablePatternError` instead
    """
    empty_case_handled = rest_case_handled = False
    for pattern in patterns:
        if isinstance(pattern, base.ListPattern):
            empty_case_handled = empty_case_handled or (
                pattern.rest is None and not pattern.initial_patterns
            )
            rest_case_handled = rest_case_handled or pattern.rest is not None
        if non_exhaustive(pattern) is None or (
            empty_case_handled and rest_case_handled
        ):
            empty_case_handled = rest_case_handled = True
            break

    if not (empty_case_handled and rest_case_handled):
        raise RefutablePatternError(PatternPosition.CASE, patterns[-1])

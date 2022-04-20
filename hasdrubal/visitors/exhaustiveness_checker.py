from asts import typed, visitors, types_ as types
from errors import InexhaustivePatternError


class ExhaustivenessChecker(visitors.TypedASTVisitor[None]):
    def visit_apply(self, node: typed.Apply) -> None:
        node.func.visit(self)
        node.arg.visit(self)

    def visit_block(self, node: typed.Block) -> None:
        for expr in node.body:
            expr.visit(self)

    def visit_cond(self, node: typed.Cond) -> None:
        node.pred.visit(self)

    def visit_define(self, node: typed.Define) -> None:
        if not is_exhaustive(node.target):
            raise InexhaustivePatternError(node, node.target)
        node.body.visit(self)

    def visit_function(self, node: typed.Function) -> None:
        if not is_exhaustive(node.param):
            raise InexhaustivePatternError(node, node.param)
        node.body.visit(self)

    def visit_list(self, node: typed.List) -> None:
        for elem in node.elements:
            elem.visit(self)

    def visit_match(self, node: typed.Match) -> None:
        node.subject.visit(self)
        exhaustive = False
        for pattern, cons in node.cases:
            exhaustive = exhaustive or is_exhaustive(pattern)
            cons.visit(self)

        if not exhaustive:
            raise InexhaustivePatternError(node, node.cases[-1][0])

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

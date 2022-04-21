from typing import Union

from asts import base, lowered, visitor
from errors import FatalInternalError
from log import logger


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
            return lowered.NativeOp(lowered.OperationTypes.NEG, arg, None)

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
        lowered = decomposed.visit(self)
        lowered.metadata["merge_parent"] = True
        return lowered

    def visit_function(self, node: base.Function) -> lowered.Function:
        param_name = f"$FuncParam_{self._param_index}"
        self._param_index += 1
        base_header = decompose_define(
            node.param, base.Name(node.span, param_name), PatternPosition.PARAMETER
        )
        header = base_header.visit(self)
        base_body = node.body.visit(self)
        if isinstance(base_body, lowered.Block):
            body = lowered.Block([*header.body, *base_body.body])
        else:
            body = lowered.Block([*header.body, base_body])
        return lowered.Function(lowered.Name(param_name), body)

    def visit_list(self, node: base.List) -> lowered.List:
        return lowered.List([elem.visit(self) for elem in node.elements])

    def visit_match(self, node: base.Match) -> lowered.LoweredASTNode:
        return make_decision_tree(node.subject, node.cases).visit(self)

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

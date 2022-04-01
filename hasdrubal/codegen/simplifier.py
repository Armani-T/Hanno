from typing import List, Tuple, Union

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


def fold_func_calls(
    node: base.Apply,
) -> Tuple[lowered.LoweredASTNode, List[lowered.LoweredASTNode]]:
    """
    Combine the base function calls (that only take 1 argument) into
    a lowered function call that can take any number of them.

    Parameters
    ----------
    node: base.FuncCall
        The top-level function call in a nested tree of them.

    Returns
    -------
    Tuple[lowered.LoweredASTNode, List[lowered.LoweredASTNode]]
        The calling function and the arguments to be passed as a list.
    """
    args = []
    result = node
    while isinstance(result, base.Apply):
        args.append(result.arg)
        result = result.func
    return result, args


class Simplifier(visitor.BaseASTVisitor[lowered.LoweredASTNode]):
    """
    Convert undefined `TypeName`s into `TypeVar`s using `defined_types`
    as a kind of symbol table to check whether a name should remain
    a `TypeName` or be converted to a `TypeVar`.
    """

    def visit_apply(self, node: base.Apply) -> Union[lowered.Apply, lowered.NativeOp]:
        func, args = fold_func_calls(node)
        func = func.visit(self)
        args = [arg.visit(self) for arg in args]
        try:
            operator = lowered.OperationTypes(func.value)
            right = args[1] if len(args) > 1 else None
            return lowered.NativeOp(operator, args[0], right)
        except (AttributeError, ValueError):
            return lowered.Apply(func, args)

    def visit_block(self, node: base.Block) -> lowered.Block:
        return lowered.Block(expr.visit(self) for expr in node.body)

    def visit_cond(self, node: base.Cond) -> lowered.Cond:
        return lowered.Cond(
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> lowered.Define:
        return lowered.Define(node.target.visit(self), node.value.visit(self))

    def visit_function(self, node: base.Function) -> lowered.Function:
        actual_node: base.ASTNode = node
        params: List[base.Name] = []
        while isinstance(actual_node, base.Function):
            params.append(actual_node.param)
            actual_node = actual_node.body
        return lowered.Function(params, actual_node.visit(self))

    def visit_list(self, node: base.List) -> lowered.List:
        return lowered.List(elem.visit(self) for elem in node.elements)

    def visit_pair(self, node: base.Pair) -> lowered.Pair:
        return lowered.Pair(node.first.visit(self), node.second.visit(self))

    def visit_name(self, node: base.Name) -> lowered.Name:
        return lowered.Name(node.value)

    def visit_scalar(self, node: base.Scalar) -> lowered.Scalar:
        return lowered.Scalar(node.value)

    def visit_type(self, node):
        logger.fatal("Tried to simplify this `Type` node in the AST: %r", node)
        raise FatalInternalError()

    def visit_unit(self, node: base.Unit) -> Union[lowered.Unit, lowered.List]:
        return lowered.Unit()

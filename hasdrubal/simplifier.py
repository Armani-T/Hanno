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
    simplifier = ASTSimplifier()
    return simplifier.run(node)


def _fold_calls(
    call: base.FuncCall,
) -> Tuple[lowered.LoweredASTNode, List[lowered.LoweredASTNode]]:
    args = []
    result: lowered.LoweredASTNode = call
    while isinstance(result, base.FuncCall):
        args.append(result.callee)
        result = result.caller
    return result, args


class ASTSimplifier(visitor.BaseASTVisitor[lowered.LoweredASTNode]):
    """
    Convert undefined `TypeName`s into `TypeVar`s using `defined_types`
    as a kind of symbol table to check whether a name should remain
    a `TypeName` or be converted to a `TypeVar`.
    """

    def visit_block(self, node: base.Block) -> lowered.Block:
        return lowered.Block(node.span, [expr.visit(self) for expr in node.body()])

    def visit_cond(self, node: base.Cond) -> lowered.Cond:
        return lowered.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> lowered.Define:
        return lowered.Define(
            node.span, node.target.visit(self), node.value.visit(self)
        )

    def visit_func_call(
        self, node: base.FuncCall
    ) -> Union[lowered.FuncCall, lowered.NativeOperation]:
        func, args = _fold_calls(node)
        func = func.visit(self)
        args = [arg.visit(self) for arg in args]

        if isinstance(func, lowered.Name) and func.value in lowered.OperationTypes:
            operator = lowered.OperationTypes(func.value)
            right = args[1] if len(args) > 1 else None
            return lowered.NativeOperation(
                node.span,
                operator,
                args[0],
                right,
            )
        return lowered.FuncCall(node.span, func, args)

    def visit_function(self, node: base.Function) -> base.Function:
        original_span = node.span
        params: List[base.Name] = []
        while isinstance(node, base.Function):
            params.append(node.param)
            node = node.body  # type: ignore
        return lowered.Function(original_span, params, node)

    def visit_name(self, node: base.Name) -> base.Name:
        return lowered.Name(node.span, node.value)

    def visit_scalar(self, node: base.Scalar) -> lowered.Scalar:
        return node

    def visit_type(self, node):
        logger.fatal("Tried to simplify this `Type` node in the AST: %r", node)
        raise FatalInternalError()

    def visit_vector(self, node: base.Vector) -> lowered.Vector:
        return lowered.Vector(
            node.span,
            node.vec_type,
            [element.visit(self) for element in node.elements],
        )

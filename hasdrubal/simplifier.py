from typing import Container

from asts import base, lowered, visitor
from errors import FatalInternalError
from log import logger


def fold_calls(call: base.FuncCall) -> lowered.FuncCall:
    """Merge several nested function calls into a single one."""
    original_span = call.span
    args = []
    while isinstance(call, base.FuncCall):
        args.append(call.callee)
        call = call.caller
    return lowered.FuncCall(original_span, call, args)


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


class ASTSimplifier(visitor.BaseASTVisitor[base.ASTNode]):
    """
    Convert undefined `TypeName`s into `TypeVar`s using `defined_types`
    as a kind of symbol table to check whether a name should remain
    a `TypeName` or be converted to a `TypeVar`.

    Attributes
    ----------
    defined_types: Container[str]
        The identifiers that are known to actually be type names.
    """

    def visit_block(self, node: base.Block) -> base.Block:
        return base.Block(node.span, [expr.visit(self) for expr in node.body()])

    def visit_cond(self, node: base.Cond) -> base.Cond:
        return base.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> base.Define:
        return base.Define(node.span, node.target.visit(self), node.value.visit(self))

    def visit_func_call(self, node: base.FuncCall):
        result = fold_calls(node)
        result.func = result.func.visit(self)
        result.args = [arg.visit(self) for arg in result.args]

        try:
            operator = lowered.OperationTypes(caller.value)
            left = result.args[0]
            right = result.args[0] if len(result.args) > 1 else None
            return NativeOperation(node.span, operator, left, right)
        except (ValueError, AttributeError):
            return result

    def visit_function(self, node: base.Function) -> base.Function:
        original_span = node.span
        params = []
        while isinstance(node, base.Function):
            params.append(node.params)
            node = node.body
        return lowered.Function(original_span, params, body)

    def visit_name(self, node: base.Name) -> base.Name:
        return base.Name(node.span, node.value)

    def visit_scalar(self, node: base.Scalar) -> base.Scalar:
        return node

    def visit_type(self, node):
        logger.fatal(
            "Tried to convert this `Type` node (%r) in the AST to bytecode.", node
        )
        raise FatalInternalError()

    def visit_vector(self, node: base.Vector) -> base.Vector:
        return base.Vector(
            node.span,
            node.vec_type,
            [element.visit(self) for element in node.elements],
        )

from typing import Container

from asts.visitor import LoweredASTVisitor
from asts import lowered

COMPARE_OPS: Container[lowered.OperationTypes] = (
    lowered.OperationTypes.EQUAL,
    lowered.OperationTypes.GREATER,
    lowered.OperationTypes.LESS,
)
MATH_OPS: Container[lowered.OperationTypes] = (
    lowered.OperationTypes.ADD,
    lowered.OperationTypes.SUB,
    lowered.OperationTypes.MUL,
    lowered.OperationTypes.DIV,
    lowered.OperationTypes.EXP,
    lowered.OperationTypes.MOD,
)


def fold_constants(tree: lowered.LoweredASTNode) -> lowered.LoweredASTNode:
    """
    Perform all trivial operations involving scalars to simplify the
    VM's work at runtime.

    Parameters
    ----------
    tree: lowered.LoweredASTNode
        The AST, possibly with trivial operations still lingering.

    Returns
    -------
    lowered.LoweredASTNode
        The same AST but with the trivial operations done.
    """
    folder = ConstantFolder()
    return folder.run(tree)


class ConstantFolder(LoweredASTVisitor[lowered.LoweredASTNode]):
    """
    Combine literal operations into a single AST node.
    """

    def visit_block(self, node: lowered.Block) -> lowered.Block:
        return lowered.Block(
            node.span,
            [expr.visit(self) for expr in node.body()],
        )

    def visit_cond(self, node: lowered.Cond) -> lowered.Cond:
        if isinstance(node.pred, lowered.Scalar):
            return node.cons.visit(self) if node.pred.value else node.else_.visit(self)
        return lowered.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: lowered.Define) -> lowered.Define:
        return lowered.Define(
            node.span,
            node.target,
            node.value.visit(self),
        )

    def visit_function(self, node: lowered.Function) -> lowered.Function:
        return lowered.Function(
            node.span,
            node.params,
            node.body.visit(self),
        )

    def visit_func_call(self, node: lowered.FuncCall) -> lowered.FuncCall:
        return lowered.FuncCall(
            node.span,
            node.func.visit(self),
            [arg.visit(self) for arg in node.args],
        )

    def visit_name(self, node: lowered.Name) -> lowered.Name:
        return node

    def visit_native_operation(
        self, node: lowered.NativeOperation
    ) -> lowered.LoweredASTNode:
        if _can_simplify_negate(node):
            return lowered.Scalar(node.span, -node.left.value)
        if _can_simplify_math_op(node):
            return fold_math(node)
        if _can_simplify_compare_op(node):
            return fold_comparison(node)
        return lowered.NativeOperation(
            node.span,
            node.operation,
            node.left,
            node.right,
        )

    def visit_scalar(self, node: lowered.Scalar) -> lowered.Scalar:
        return node

    def visit_vector(self, node: lowered.Vector) -> lowered.Vector:
        return lowered.Vector(
            node.span,
            node.vec_type,
            [elem.visit(self) for elem in node.elements],
        )


_can_simplify_compare_op = lambda node: (
    node.operation in COMPARE_OPS
    and isinstance(node.left, lowered.Scalar)
    and isinstance(node.left, lowered.Scalar)
)
_can_simplify_math_op = lambda node: (
    node.operation in MATH_OPS
    and isinstance(node.left, lowered.Scalar)
    and isinstance(node.right, lowered.Scalar)
)
_can_simplify_negate = lambda node: (
    node.operation == lowered.OperationTypes.NEG
    and isinstance(node.left, lowered.Scalar)
)

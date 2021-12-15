from operator import add, floordiv, mod, mul, sub, truediv
from typing import Container, Tuple, Union

from asts.base import ValidScalarTypes
from asts.visitor import LoweredASTVisitor
from asts import lowered
from scope import Scope

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
    """Combine literal operations into a single AST node."""

    def __init__(self) -> None:
        self.current_scope: Scope[lowered.Scalar] = Scope(None)

    @staticmethod
    def null_node(span: Tuple[int, int]):
        """
        Generate a harmless AST node that does nothing and will be
        removed by a later optimisation pass.
        """
        return lowered.Vector.unit(span)

    def visit_block(self, node: lowered.Block) -> lowered.Block:
        self.current_scope = self.current_scope.down()
        result = lowered.Block(node.span, [expr.visit(self) for expr in node.body])
        self.current_scope = self.current_scope.up()
        return result

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
        value = node.value.visit(self)
        if node.target not in self.current_scope and isinstance(value, lowered.Scalar):
            self.current_scope[node.target] = value
            return self.null_node(node.span)
        return lowered.Define(node.span, node.target, value)

    def visit_function(self, node: lowered.Function) -> lowered.Function:
        self.current_scope = self.current_scope.down()
        body = node.body.visit(self)
        self.current_scope = self.current_scope.up()
        return lowered.Function(node.span, node.params, body)

    def visit_func_call(self, node: lowered.FuncCall) -> lowered.FuncCall:
        return lowered.FuncCall(
            node.span,
            node.func.visit(self),
            [arg.visit(self) for arg in node.args],
        )

    def visit_name(self, node: lowered.Name) -> Union[lowered.Name, lowered.Scalar]:
        return self.current_scope[node] if node in self.current_scope else node

    def visit_native_operation(
        self, node: lowered.NativeOperation
    ) -> lowered.LoweredASTNode:
        left = node.left.visit(self)
        right = None if node.right is None else node.right.visit(self)
        node = lowered.NativeOperation(node.span, node.operation, left, right)
        if _can_simplify_negate(node):
            return lowered.Scalar(node.span, -left.value)
        if right is not None and _can_simplify_math_op(node):
            return lowered.Scalar(node.span, fold_math(node.operation, left, right))
        if right is not None and _can_simplify_compare_op(node):
            success, result = fold_comparison(node.operation, left, right)
            return lowered.Scalar(node.span, result) if success else node
        return node

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


def fold_math(
    operation: lowered.OperationTypes, left: lowered.Scalar, right: lowered.Scalar
) -> ValidScalarTypes:
    """
    Perform any mathematical expressions in the AST that evaluate to a
    constant.

    Parameters
    ----------
    operation: lowered.OperationTypes
        The mathematical operation to do.
    left: lowered.Scalar
        The left hand operand of the mathematical operation.
    right: lowered.Scalar
        The right hand operand of the mathematical operation.

    Returns
    -------
    ValidScalarTypes
        The constant scalar value of the operation. It will need to be
        wrapped inside a `Scalar` node since this is just the raw value.
    """
    if operation == lowered.OperationTypes.DIV:
        func = floordiv if isinstance(left.value, int) else truediv
    else:
        func = {
            lowered.OperationTypes.ADD: add,
            lowered.OperationTypes.SUB: sub,
            lowered.OperationTypes.MUL: mul,
            lowered.OperationTypes.EXP: pow,
            lowered.OperationTypes.MOD: mod,
        }[operation]
    return func(left.value, right.value)


def fold_comparison(
    operation: lowered.OperationTypes, left: lowered.Scalar, right: lowered.Scalar
) -> Tuple[bool, bool]:
    """
    Perform any comparison operations in the AST that evaluate to a
    constant.

    Parameters
    ----------
    operation: lowered.OperationTypes
        The comparison operation to do.
    left: lowered.Scalar
        The left hand operand of the comparison operation.
    right: lowered.Scalar
        The right hand operand of the comparison operation.

    Returns
    -------
    Tuple[bool, bool]
        Whether to replace the operation node and the constant scalar
        value of performing the operation if it should be replaced. If
        it shouldn't be replaced, this value is automatically `False`.
    """
    if operation == lowered.OperationTypes.EQUAL:
        return True, left.value == right.value
    if operation == lowered.OperationTypes.GREATER:
        return True, left.value > right.value  # type: ignore
    if operation == lowered.OperationTypes.LESS:
        return True, left.value < right.value  # type: ignore
    return False, False

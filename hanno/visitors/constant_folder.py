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
    """
    Combine literal operations into a single AST node.

    Attributes
    ----------
    current_scope: Scope[lowered.Scalar]
        Stores all the names with constant values defined in the scope.
    """

    def __init__(self) -> None:
        self.current_scope: Scope[lowered.Scalar] = Scope(None)

    def visit_apply(self, node: lowered.Apply) -> lowered.Apply:
        return lowered.Apply(node.func.visit(self), node.arg.visit(self))

    def visit_block(self, node: lowered.Block) -> lowered.ASTNode:
        self.current_scope = self.current_scope.down()
        body = tuple(
            filter(
                lambda expr: not expr.metadata.get("delete", False),
                map(lambda expr: expr.visit(self), node.body),
            )
        )
        self.current_scope = self.current_scope.up()
        return (
            lowered.Unit()
            if not body
            else body[0] if len(body) == 1 else lowered.Block(body)
        )

    def visit_cond(self, node: lowered.Cond) -> lowered.Cond:
        pred = node.pred.visit(self)
        if isinstance(pred, lowered.Scalar):
            return node.cons.visit(self) if pred.value else node.else_.visit(self)
        return lowered.Cond(pred, node.cons.visit(self), node.else_.visit(self))

    def visit_define(self, node: lowered.Define) -> lowered.LoweredASTNode:
        value = node.value.visit(self)
        if isinstance(value, lowered.Scalar):
            self.current_scope[node.target] = value
            node.metadata["delete"] = True
            return node
        return lowered.Define(node.target, value)

    def visit_function(self, node: lowered.Function) -> lowered.Function:
        self.current_scope = self.current_scope.down()
        body = node.body.visit(self)
        self.current_scope = self.current_scope.up()
        return lowered.Function(node.param, body)

    def visit_list(self, node: lowered.List) -> lowered.List:
        return lowered.List([elem.visit(self) for elem in node.elements])

    def visit_pair(self, node: lowered.Pair) -> lowered.Pair:
        return lowered.Pair(node.first.visit(self), node.second.visit(self))

    def visit_name(self, node: lowered.Name) -> Union[lowered.Name, lowered.Scalar]:
        return self.current_scope[node] if node in self.current_scope else node

    def visit_native_op(self, node: lowered.NativeOp) -> lowered.LoweredASTNode:
        left = node.left.visit(self)
        right = None if node.right is None else node.right.visit(self)
        node = lowered.NativeOp(node.operation, left, right)
        if _can_simplify_negate(node):
            return lowered.Scalar(-left.value)
        if _can_simplify_math_op(node):
            return lowered.Scalar(fold_math(node.operation, left, right))
        if _can_simplify_compare_op(node):
            success, result = fold_comparison(node.operation, left, right)
            return lowered.Scalar(result) if success else node
        return node

    def visit_scalar(self, node: lowered.Scalar) -> lowered.Scalar:
        return node

    def visit_unit(self, node: lowered.Unit) -> lowered.Unit:
        return node


_can_simplify_compare_op = lambda node: (
    node.operation in COMPARE_OPS
    and isinstance(node.left, lowered.Scalar)
    and isinstance(node.right, lowered.Scalar)
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
        The left-hand operand of the mathematical operation.
    right: lowered.Scalar
        The right-hand operand of the mathematical operation.

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
        The left-hand operand of the comparison operation.
    right: lowered.Scalar
        The right-hand operand of the comparison operation.

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

from asts.visitor import BaseASTVisitor
from asts import base


class StringExpander(BaseASTVisitor[base.ASTNode]):
    """
    Convert unexpanded Unicode escapes into the correct Unicode
    character.
    """

    def visit_block(self, node: base.Block) -> base.Block:
        return base.Block(
            node.span,
            [expr.visit(self) for expr in node.body],
        )

    def visit_cond(self, node: base.Cond) -> base.Cond:
        return base.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> base.Define:
        return base.Define(
            node.span,
            node.target.visit(self),
            node.value.visit(self),
        )

    def visit_function(self, node: base.Function) -> base.Function:
        return base.Function(
            node.span,
            node.param.visit(self),
            node.body.visit(self),
        )

    def visit_func_call(self, node: base.FuncCall) -> base.FuncCall:
        return base.FuncCall(
            node.span,
            node.caller.visit(self),
            node.callee.visit(self),
        )

    def visit_name(self, node: base.Name) -> base.Name:
        return node

    def visit_scalar(self, node: base.Scalar) -> base.Scalar:
        if isinstance(node.value, str):
            return base.Scalar(node.span, _expand(node.value))
        return node

    def visit_vector(self, node: base.Vector) -> base.Vector:
        return base.Vector(
            node.span,
            node.vec_type,
            [elem.visit(self) for elem in node.elements],
        )

from typing import Container

from asts.typed import Name as TypedName
from asts import base, visitor, types_ as types

PREDEFINED_TYPES: Container[str] = (
    ",",
    "->",
    "Bool",
    "Float",
    "Int",
    "List",
    "String",
    "Unit",
)


def resolve_type_vars(
    node: base.ASTNode,
    defined_types: Container[str] = PREDEFINED_TYPES,
) -> base.ASTNode:
    """
    Convert `TypeName`s in the AST to `TypeVar`s using `defined_types`
    to determine which ones should be converted.

    Parameters
    ----------
    node: ASTNode
        The AST where `TypeName`s will be searched for.
    defined_types: Container[str] = PREDEFINED_TYPES
        If a `TypeName` is inside this, it will remain a `TypeName`.

    Returns
    -------
    ASTNode
        The AST but with the appropriate `TypeName`s converted to
        `TypeVar`s.
    """
    resolver = TypeVarResolver(defined_types)
    return resolver.run(node)


class TypeVarResolver(visitor.BaseASTVisitor[base.ASTNode]):
    """
    Convert undefined `TypeName`s into `TypeVar`s using `defined_types`
    as a kind of symbol table to check whether a name should remain
    a `TypeName` or be converted to a `TypeVar`.

    Attributes
    ----------
    defined_types: Container[str]
        The identifiers that are known to actually be type names.
    """

    def __init__(self, defined_types: Container[str] = PREDEFINED_TYPES) -> None:
        self.defined_types: Container[str] = defined_types

    def visit_block(self, node: base.Block) -> base.Block:
        return base.Block(node.span, [expr.visit(self) for expr in node.body])

    def visit_cond(self, node: base.Cond) -> base.Cond:
        return base.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> base.Define:
        return base.Define(node.span, node.target.visit(self), node.value.visit(self))

    def visit_func_call(self, node: base.FuncCall) -> base.FuncCall:
        return base.FuncCall(
            node.span,
            node.caller.visit(self),
            node.callee.visit(self),
        )

    def visit_function(self, node: base.Function) -> base.Function:
        return base.Function(node.span, node.param.visit(self), node.body.visit(self))

    def visit_name(self, node: base.Name) -> base.Name:
        if isinstance(node, TypedName):
            return TypedName(node.span, node.type_.visit(self), node.value)
        return node

    def visit_scalar(self, node: base.Scalar) -> base.Scalar:
        return node

    def visit_type(self, node: types.Type) -> types.Type:
        if isinstance(node, types.TypeApply):
            return types.TypeApply(
                node.span,
                node.caller.visit(self),
                node.callee.visit(self),
            )
        if isinstance(node, types.TypeName) and node.value not in self.defined_types:
            return types.TypeVar(node.span, node.value)
        if isinstance(node, types.TypeScheme):
            return types.TypeScheme(node.actual_type.visit(self), node.bound_types)
        return node

    def visit_vector(self, node: base.Vector) -> base.Vector:
        return base.Vector(
            node.span,
            node.vec_type,
            [element.visit(self) for element in node.elements],
        )

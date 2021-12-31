from functools import reduce
from typing import List, Tuple, Union

from asts import base, typed, visitor
from asts.types_ import Type, TypeApply, TypeName, TypeVar
from log import logger
from scope import OPERATOR_TYPES, Scope
from . import utils

TypedNodes = Union[Type, typed.TypedASTNode]

star_map = lambda func, seq: (func(*args) for args in seq)


def infer_types(tree: base.ASTNode) -> typed.TypedASTNode:
    """
    Fill up all the `type_` attrs in the AST with type annotations.

    Parameters
    ----------
    tree: ASTNode
        The AST without any type annotations.

    Raises
    ------
    TypeMismatchError
        The error thrown when the engine is unable to unify 2 types.

    Returns
    -------
    ASTNode
        The AST with type annotations.
    """
    generator = ConstraintGenerator()
    tree = generator.run(tree)
    substitutions = (utils.unify(left, right) for left, right in generator.equations)
    full_substitution: utils.Substitution = reduce(
        utils.merge_substitutions, substitutions, {}
    )
    logger.debug("substitution: %r", full_substitution)
    substitutor = Substitutor(full_substitution)
    return substitutor.run(tree)


class ConstraintGenerator(visitor.BaseASTVisitor[TypedNodes]):
    """
    Generate the type equations used during unification.

    Attributes
    ----------
    current_scope: Scope[Type]
        The types of all the variables found in the AST in the
        current lexical scope.
    equations: Sequence[Equation]
        The type equations that have been generated from the AST.

    Notes
    -----
    - This visitor class puts all the equations together in a global
      list since type vars are considered unique unless explicitly
      shared.
    - The only invariant that this class has is that no AST node which
      has passed through it should have its `type_` attr = `None`.
    """

    main_type = TypeApply.func(
        (6, 25),
        TypeApply((6, 18), TypeName((6, 10), "List"), TypeName((6, 10), "String")),
        TypeName((22, 25), "Int"),
    )
    dont_generalise = {"main"}

    def __init__(self) -> None:
        self.equations: List[Tuple[Type, Type]] = []
        self.current_scope: Scope[Type] = Scope(OPERATOR_TYPES)
        self.current_scope[base.Name((0, 0), "main")] = self.main_type

    def _push(self, *args: Tuple[Type, Type]) -> None:
        self.equations += args

    def visit_block(self, node: base.Block) -> typed.Block:
        self.current_scope = self.current_scope.down()
        body = [expr.visit(self) for expr in node.body]
        self.current_scope = self.current_scope.up()
        if body:
            return typed.Block(node.span, body[-1].type_, body)
        return typed.Vector.unit(node.span)

    def visit_cond(self, node: base.Cond) -> typed.Cond:
        pred = node.pred.visit(self)
        cons = node.cons.visit(self)
        else_ = node.else_.visit(self)
        self._push(
            (pred.type_, TypeName(pred.span, "Bool")),
            (cons.type_, else_.type_),
        )
        return typed.Cond(node.span, cons.type_, pred, cons, else_)

    def visit_define(self, node: base.Define) -> typed.Define:
        initial_node_type = (
            self.current_scope[node.target]
            if node.target in self.current_scope
            else node.target.type_
            if isinstance(node.target, typed.Name)
            else TypeVar.unknown(node.target.span)
        )
        self.current_scope[node.target] = initial_node_type
        value = node.value.visit(self)
        node_type = (
            value.type_
            if node.target in self.dont_generalise
            else utils.generalise(value.type_)
        )
        self._push((initial_node_type, node_type))

        target = typed.Name(node.target.span, node_type, node.target.value)
        self.current_scope[target] = node_type
        return typed.Define(node.span, node_type, target, value)

    def visit_function(self, node: base.Function) -> typed.Function:
        self.current_scope = self.current_scope.down()
        param_type = TypeVar.unknown(node.span)
        if isinstance(node.param, typed.Name):
            self._push((node.param.type_, param_type))

        param = typed.Name(node.param.span, param_type, node.param.value)
        self.current_scope[node.param] = param_type
        body = node.body.visit(self)
        self.current_scope = self.current_scope.up()
        return typed.Function(
            node.span, TypeApply.func(node.span, param_type, body.type_), param, body
        )

    def visit_func_call(self, node: base.FuncCall) -> typed.FuncCall:
        node_type = TypeVar.unknown(node.span)
        caller = node.caller.visit(self)
        callee = node.callee.visit(self)
        self._push((caller.type_, TypeApply.func(node.span, callee.type_, node_type)))
        return typed.FuncCall(node.span, node_type, caller, callee)

    def visit_name(self, node: base.Name) -> typed.Name:
        if isinstance(node, typed.Name):
            return node
        node_type = utils.instantiate(self.current_scope[node])
        return typed.Name(node.span, node_type, node.value)

    def visit_scalar(self, node: base.Scalar) -> typed.Scalar:
        name_map = {bool: "Bool", float: "Float", int: "Int", str: "String"}
        node_type = TypeName(node.span, name_map[type(node.value)])
        return typed.Scalar(node.span, node_type, node.value)

    def visit_type(self, node: Type) -> Type:
        return node

    def visit_vector(self, node: base.Vector) -> typed.Vector:
        elements = [elem.visit(self) for elem in node.elements]

        if node.vec_type == base.VectorTypes.TUPLE:
            node_type = TypeApply.tuple_(node.span, [elem.type_ for elem in elements])
            return typed.Vector(node.span, node_type, base.VectorTypes.TUPLE, elements)

        elem_type = elements[0].type_ if elements else TypeVar.unknown(node.span)
        constraints = [(elem_type, elem.type_) for elem in elements]
        self._push(*constraints)

        node_type = TypeApply(node.span, TypeName(node.span, "List"), elem_type)
        return typed.Vector(node.span, node_type, base.VectorTypes.LIST, elements)


class Substitutor(visitor.TypedASTVisitor[TypedNodes]):
    """
    Replace type vars in the AST with actual types.

    Attributes
    ----------
    substitution: Substitution
        The known mappings between type vars and actual types as
        generated by an external unifier.
    """

    def __init__(self, substitution: utils.Substitution) -> None:
        self.substitution: utils.Substitution = substitution

    def visit_block(self, node: typed.Block) -> typed.Block:
        return typed.Block(
            node.span,
            node.type_.substitute(self.substitution),
            [expr.visit(self) for expr in node.body],
        )

    def visit_cond(self, node: typed.Cond) -> typed.Cond:
        return typed.Cond(
            node.span,
            node.type_.substitute(self.substitution),
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: typed.Define) -> typed.Define:
        value = node.value.visit(self)
        node_type = utils.generalise(value.type_.substitute(self.substitution))
        return typed.Define(
            node.span,
            node_type,
            typed.Name(node.target.span, node_type, node.target.value),
            value,
        )

    def visit_function(self, node: typed.Function) -> typed.Function:
        return typed.Function(
            node.span,
            node.type_.substitute(self.substitution),
            node.param.visit(self),
            node.body.visit(self),
        )

    def visit_func_call(self, node: typed.FuncCall) -> typed.FuncCall:
        return typed.FuncCall(
            node.span,
            node.type_.substitute(self.substitution),
            node.caller.visit(self),
            node.callee.visit(self),
        )

    def visit_name(self, node: typed.Name) -> typed.Name:
        return typed.Name(
            node.span,
            node.type_.substitute(self.substitution),
            node.value,
        )

    def visit_scalar(self, node: typed.Scalar) -> typed.Scalar:
        return node

    def visit_type(self, node: Type) -> Type:
        return node

    def visit_vector(self, node: typed.Vector) -> typed.Vector:
        return typed.Vector(
            node.span,
            node.type_.substitute(self.substitution),
            node.vec_type,
            [elem.visit(self) for elem in node.elements],
        )

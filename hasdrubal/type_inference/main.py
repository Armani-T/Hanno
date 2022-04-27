from functools import reduce
from typing import List, Tuple, Union

from asts import base, typed, visitor
from asts.types_ import Type, TypeApply, TypeName, TypeVar
from log import logger
from scope import OPERATOR_TYPES, Scope
from . import utils

Constraints = List[Tuple[Type, Type]]
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
    tree, constraints = generator.run(tree)
    substitutions = (utils.unify(left, right) for left, right in constraints)
    full_substitution: utils.Substitution = reduce(
        utils.merge_substitutions, substitutions, {}
    )
    logger.debug("substitution: %r", full_substitution)
    substitutor = Substitutor(full_substitution)
    return substitutor.run(tree)


class ConstraintGenerator(visitor.BaseASTVisitor[Tuple[TypedNodes, Constraints]]):
    """
    Generate the type equations used during unification.

    Attributes
    ----------
    current_scope: Scope[Type]
        The types of all the variables found in the AST in the
        current lexical scope.

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

    def __init__(self) -> None:
        self.current_scope: Scope[Type] = Scope(OPERATOR_TYPES)
        self.current_scope[base.Name((0, 0), "main")] = self.main_type

    def visit_apply(self, node: base.Apply) -> Tuple[typed.Apply, Constraints]:
        node_type = TypeVar.unknown(node.span)
        caller, caller_constraints = node.func.visit(self)
        callee, callee_constraints = node.arg.visit(self)
        equations = [
            *callee_constraints,
            *caller_constraints,
            (caller.type_, TypeApply.func(node.span, callee.type_, node_type)),
        ]
        return typed.Apply(node.span, node_type, caller, callee), equations

    def visit_block(self, node: base.Block) -> Tuple[typed.Block, Constraints]:
        exprs = []
        equations = []
        self.current_scope = self.current_scope.down()
        for expr in node.body:
            expr, expr_constraints = expr.visit(self)
            exprs.append(expr)
            equations += expr_constraints

        self.current_scope = self.current_scope.up()
        return typed.Block(node.span, exprs[-1].type_, exprs), equations

    def visit_cond(self, node: base.Cond) -> Tuple[typed.Cond, Constraints]:
        pred, pred_constraints = node.pred.visit(self)
        cons, cons_constraints = node.cons.visit(self)
        else_, else_constraints = node.else_.visit(self)
        equations = [
            *pred_constraints,
            *cons_constraints,
            *else_constraints,
            (pred.type_, TypeName(pred.span, "Bool")),
            (cons.type_, else_.type_),
        ]
        return typed.Cond(node.span, cons.type_, pred, cons, else_), equations

    def visit_define(self, node: base.Define) -> Tuple[typed.Define, Constraints]:
        new_names, target_type = utils.pattern_infer(node.target, self.current_scope)
        self.current_scope.update(new_names)
        value, value_constraints = node.value.visit(self)
        substitution = reduce(
            utils.merge_substitutions,
            (utils.unify(left, right) for left, right in value_constraints),
            {},
        )
        node_type = utils.generalise(utils.substitute(value.type_, substitution))
        equations = [*value_constraints, (target_type, node_type)]
        if isinstance(node.target, base.FreeName):
            self.current_scope[node.target] = node_type

        return typed.Define(node.span, node_type, node.target, value), equations

    def visit_function(self, node: base.Function) -> Tuple[typed.Function, Constraints]:
        self.current_scope = self.current_scope.down()
        new_names, param_type = utils.pattern_infer(node.param, self.current_scope)
        self.current_scope.update(new_names)
        body, body_constraints = node.body.visit(self)
        self.current_scope = self.current_scope.up()
        new_node = typed.Function(
            node.span,
            TypeApply.func(node.span, param_type, body.type_),
            node.param,
            body,
        )
        return new_node, body_constraints

    def visit_list(self, node: base.List) -> Tuple[typed.List, Constraints]:
        elements = []
        equations = []
        elem_type = elements[0].type_ if elements else TypeVar.unknown(node.span)
        for elem in node.elements:
            new_elem, elem_constraints = elem.visit(self)
            elements.append(new_elem)
            equations += elem_constraints
            equations.append((elem_type, new_elem.type_))

        node_type = TypeApply(node.span, TypeName(node.span, "List"), elem_type)
        return typed.List(node.span, node_type, elements), equations

    def visit_match(self, node: base.Match) -> Tuple[typed.Match, Constraints]:
        subject, equations = node.subject.visit(self)
        cons_type = TypeVar.unknown(node.span)
        cases = []
        for pred, cons in node.cases:
            new_names, pattern_type = utils.pattern_infer(pred, self.current_scope)
            equations.append((subject.type_, pattern_type))

            self.current_scope = self.current_scope.down()
            self.current_scope.update(new_names)
            cons, cons_constraints = cons.visit(self)
            equations += cons_constraints
            equations.append((cons_type, cons.type_))
            self.current_scope = self.current_scope.up()
            cases.append((pred, cons))

        return typed.Match(node.span, cons_type, subject, cases), equations

    def visit_pair(self, node: base.Pair) -> Tuple[typed.Pair, Constraints]:
        first, first_constraints = node.first.visit(self)
        second, second_constraints = node.second.visit(self)
        node_type = TypeApply.tuple_(node.span, [first.type_, second.type_])
        return (
            typed.Pair(node.span, node_type, first, second),
            [*first_constraints, *second_constraints],
        )

    def visit_pattern(
        self, node: base.Pattern
    ) -> Tuple[typed.TypedASTNode, Constraints]:
        raise ValueError("This function should never be called!")

    def visit_name(self, node: base.Name) -> Tuple[typed.Name, Constraints]:
        node_type = utils.instantiate(self.current_scope[node])
        return typed.Name(node.span, node_type, node.value), []

    def visit_scalar(self, node: base.Scalar) -> Tuple[typed.Scalar, Constraints]:
        name_map = {bool: "Bool", float: "Float", int: "Int", str: "String"}
        node_type = TypeName(node.span, name_map[type(node.value)])
        return typed.Scalar(node.span, node_type, node.value), []

    def visit_type(self, node: Type) -> Tuple[Type, Constraints]:
        return node, []

    def visit_unit(self, node: base.Unit) -> Tuple[typed.Unit, Constraints]:
        return typed.Unit(node.span), []


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

    def visit_apply(self, node: typed.Apply) -> typed.Apply:
        return typed.Apply(
            node.span,
            utils.substitute(node.type_, self.substitution),
            node.func.visit(self),
            node.arg.visit(self),
        )

    def visit_block(self, node: typed.Block) -> typed.Block:
        return typed.Block(
            node.span,
            utils.substitute(node.type_, self.substitution),
            [expr.visit(self) for expr in node.body],
        )

    def visit_cond(self, node: typed.Cond) -> typed.Cond:
        return typed.Cond(
            node.span,
            utils.substitute(node.type_, self.substitution),
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: typed.Define) -> typed.Define:
        value = node.value.visit(self)
        return typed.Define(
            node.span, utils.generalise(value.type_), node.target, value
        )

    def visit_function(self, node: typed.Function) -> typed.Function:
        return typed.Function(
            node.span,
            utils.substitute(node.type_, self.substitution),
            node.param,
            node.body.visit(self),
        )

    def visit_list(self, node: typed.List) -> typed.List:
        return typed.List(
            node.span,
            utils.substitute(node.type_, self.substitution),
            [elem.visit(self) for elem in node.elements],
        )

    def visit_match(self, node: typed.Match) -> typed.Match:
        return typed.Match(
            node.span,
            utils.substitute(node.type_, self.substitution),
            node.subject.visit(self),
            [(pred, cons.visit(self)) for pred, cons in node.cases],
        )

    def visit_pair(self, node: typed.Pair) -> typed.Pair:
        return typed.Pair(
            node.span,
            utils.substitute(node.type_, self.substitution),
            node.first.visit(self),
            node.second.visit(self),
        )

    def visit_name(self, node: typed.Name) -> typed.Name:
        return typed.Name(
            node.span,
            utils.substitute(node.type_, self.substitution),
            node.value,
        )

    def visit_scalar(self, node: typed.Scalar) -> typed.Scalar:
        return node

    def visit_type(self, node: Type) -> Type:
        return node

    def visit_unit(self, node: typed.Unit) -> typed.Unit:
        return node

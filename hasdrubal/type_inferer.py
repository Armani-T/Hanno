from functools import reduce
from typing import List, Mapping, Set, Tuple, Union

from asts import base, typed, visitor
from asts.types_ import Type, TypeApply, TypeName, TypeScheme, TypeVar
from errors import CircularTypeError, TypeMismatchError
from log import logger
from pprint_ import show_type
from scope import DEFAULT_OPERATOR_TYPES, Scope

Substitution = Mapping[TypeVar, Type]
TypeOrSub = Union[Type, Substitution]
TypedNodes = Union[Type, typed.TypedASTNode]

star_map = lambda func, seq: (func(*args) for args in seq)

main_type = TypeApply.func(
    (0, 19),
    TypeApply((0, 12), TypeName((0, 4), "List"), TypeName((0, 4), "String")),
    TypeName((16, 19), "Int"),
)

Type.__str__ = Type.__repr__ = show_type  # type: ignore
# NOTE: I'm doing this here to avoid circular imports and because here
# is the first place that a type object might be printed out.


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
    substitutions = (unify(left, right) for left, right in generator.equations)
    full_substitution: Substitution = reduce(merge_substitutions, substitutions, {})
    logger.debug("final substitution: %s", full_substitution)
    substitutor = Substitutor(full_substitution)
    return substitutor.run(tree)


def unify(left: Type, right: Type) -> Substitution:
    """
    Build a substitution using two types or fail if it's unsatisfiable.

    Parameters
    ----------
    left: Type
        One of the types to be unified.
    right: Type
        One of the types to be unified.

    Raises
    ------
    TypeMismatchError
        The error thrown when `left` and `right` can't be unified.

    Returns
    -------
    Substitution
        The result of unifying `left` and `right`.
    """
    result = _unify(left, right)
    logger.debug("(%s) ~ (%s) => %s", left, right, result)
    return result


def _unify(left, right):
    if isinstance(left, TypeVar):
        if left.strong_eq(right):
            return {}
        if left in right:
            raise CircularTypeError(left, right)
        return {left: right}
    if isinstance(right, TypeVar):
        return unify(right, left)  # pylint: disable=W1114
    if isinstance(left, TypeName) and left == right:
        return {}
    if isinstance(left, TypeApply) and isinstance(right, TypeApply):
        return merge_substitutions(
            unify(left.caller, right.caller),
            unify(left.callee, right.callee),
        )
    raise TypeMismatchError(left, right)


def merge_substitutions(left: Substitution, right: Substitution) -> Substitution:
    """
    Combine two substitutions into one bigger one without losing any
    data.

    Notes
    -----
    - This function can't be implemented using `dict.update` because
      that method would silently remove duplicate keys.

    Parameters
    ----------
    left: Substitution
        One of the substitutions to be merged.
    right: Substitution
        The other substitution to be merged.

    Returns
    -------
    Substitution
        The substitution that contains both left and right plus any
        other replacements necessary to ensure duplicate keys unify.
    """
    if left and right:
        solution_parts = (
            unify(value, right[key]) for key, value in left.items() if key in right
        )
        merged_parts: Substitution = reduce(merge_substitutions, solution_parts, {})
        full_sub = {**left, **right, **merged_parts}
        return {key: value.substitute(full_sub) for key, value in full_sub.items()}
    return left or right


def instantiate(type_: Type) -> Type:
    """
    Unwrap the argument if it's a type scheme.

    Parameters
    ----------
    type_: TypeScheme
        The type that will be instantiated if it's an `TypeScheme`.

    Returns
    -------
    Type
        The instantiated type (generated from the `actual_type` attr).
    """
    if isinstance(type_, TypeScheme):
        return type_.actual_type.substitute(
            {var: TypeVar.unknown(type_.span) for var in type_.bound_types}
        )
    return type_


def generalise(type_: Type) -> Type:
    """
    Turn any old type into a type scheme.

    Parameters
    ----------
    type_: Type
        The type containing free type variables.

    Returns
    -------
    TypeScheme
        The type scheme with the free type variables quantified over
        it.
    """
    free_vars = find_free_vars(type_)
    return fold_scheme(TypeScheme(type_, free_vars)) if free_vars else type_


def find_free_vars(type_: Type) -> Set[TypeVar]:
    """
    Find all the free vars inside `type_`.

    Parameters
    ----------
    type_: Type
        The type containing free type variables.

    Returns
    -------
    Set[TypeVar]
        All the free type variables found in `type_`.
    """
    if isinstance(type_, TypeApply):
        return find_free_vars(type_.caller) | find_free_vars(type_.callee)
    if isinstance(type_, TypeName):
        return set()
    if isinstance(type_, TypeScheme):
        return find_free_vars(type_.actual_type) - type_.bound_types
    if isinstance(type_, TypeVar):
        return {type_}
    raise TypeError(f"{type_} is an invalid subtype of Type.")


def fold_scheme(scheme: TypeScheme) -> TypeScheme:
    """Merge several nested type schemes into a single one."""
    if isinstance(scheme.actual_type, TypeScheme):
        inner = fold_scheme(scheme.actual_type)
        return TypeScheme(inner.actual_type, inner.bound_types | scheme.bound_types)
    return scheme


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

    def __init__(self) -> None:
        self.equations: List[Tuple[Type, Type]] = []
        self.current_scope: Scope[Type] = Scope(DEFAULT_OPERATOR_TYPES)

    def run(self, node):
        self.current_scope[base.Name((0, 0), "main")] = main_type
        return node.visit(self)

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
        value = node.value.visit(self)
        node_type = generalise(value.type_)
        if isinstance(node.target, typed.Name):
            target = node.target
            self._push((node.target.type_, node_type))
        else:
            target = typed.Name(node.target.span, node_type, node.target.value)

        if target in self.current_scope:
            self._push((node_type, self.current_scope[node.target]))

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
        node_type = instantiate(self.current_scope[node])
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

    def __init__(self, substitution: Substitution) -> None:
        self.substitution: Substitution = substitution

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
        node_type = generalise(value.type_.substitute(self.substitution))
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

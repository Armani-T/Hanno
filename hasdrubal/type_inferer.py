from functools import reduce
from operator import or_
from typing import cast, Mapping, Union

from errors import TypeMismatchError
from scope import DEFAULT_OPERATOR_TYPES, Scope
from visitor import NodeVisitor
from asts import base
from asts import typed
from asts.types import FuncType, GenericType, Type, TypeScheme, TypeVar

Substitution = Mapping[TypeVar, Type]
TypeOrSub = Union[Type, Substitution]

star_map = lambda func, seq: map(lambda args: func(*args), seq)

_self_substitute = lambda substitution: {
    var: substitute(type_, substitution)
    for var, type_ in substitution.items()
    if type_ is not None
}


def infer_types(tree: base.ASTNode) -> base.ASTNode:
    """
    Fill up all the `type_` attrs in the AST with type annotations.

    Parameters
    ----------
    tree: ast_.ASTNode
        The AST without any type annotations.

    Raises
    ------
    errors.TypeMismatchError
        The error thrown when the engine is unable to unify 2 types.

    Returns
    -------
    ast_.ASTNode
        The AST with type annotations.
    """
    inserter = _Inserter()
    generator = _EquationGenerator()
    tree = inserter.run(tree)
    generator.run(tree)
    substitution: Substitution
    substitution = reduce(_merge_subs, star_map(unify, generator.equations), {})
    substitution = _self_substitute(substitution)
    return _Substitutor(substitution).run(tree)


def unify(left: Type, right: Type) -> Substitution:
    """
    Build a substitution using two types or fail if it's unsatisfiable.

    Parameters
    ----------
    left: ast_.Type
        One of the types to be unified.
    right: ast_.Type
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
    left, right = instantiate(left), instantiate(right)
    if isinstance(left, TypeVar) or isinstance(right, TypeVar):
        return _unify_type_vars(left, right)
    if isinstance(left, GenericType) and isinstance(right, GenericType):
        return _unify_generics(left, right)
    if isinstance(left, FuncType) and isinstance(right, FuncType):
        return _unify_func_types(left, right)
    raise TypeMismatchError(left, right)


def _unify_type_vars(left: Type, right: Type) -> Substitution:
    left_is_var = isinstance(left, TypeVar)
    right_is_var = isinstance(right, TypeVar)
    if left_is_var and right_is_var and left.value == right.value:  # type: ignore
        return {}
    if left_is_var:
        return {cast(TypeVar, left): right}
    if right_is_var:
        return {cast(TypeVar, right): left}
    raise TypeMismatchError(left, right)


def _unify_generics(left: GenericType, right: GenericType) -> Substitution:
    if left.base != right.base or len(left.args) != len(right.args):
        raise TypeMismatchError(left, right)

    substitution: Substitution = {}
    for left_arg, right_arg in zip(left.args, right.args):
        result = unify(left_arg, right_arg)
        substitution = _merge_subs(substitution, result)
    return substitution


def _unify_func_types(left: FuncType, right: FuncType) -> Substitution:
    left_sub = unify(left.left, right.left)
    right_sub = unify(
        substitute(left.right, left_sub),
        substitute(right.right, left_sub),
    )
    return _merge_subs(left_sub, right_sub)


def _merge_subs(left: Substitution, right: Substitution) -> Substitution:
    conflicts = {
        key: (left[key], right[key])
        for key in left
        if key in right and left[key] != right[key]
    }
    solved: Substitution = reduce(_merge_subs, star_map(unify, conflicts.values()), {})
    return left | right | solved


def substitute(type_: Type, substitution: Substitution) -> Type:
    """
    Replace free type vars in `type_` with the values in `substitution`

    Parameters
    ----------
    type_: ast_.Type
        The type containing free type vars.
    substitution: Substitution
        The mapping to used to replace the free type vars.

    Returns
    -------
    ast_.Type
        The type without any free type variables.
    """
    if isinstance(type_, TypeVar):
        type_ = substitution.get(type_, type_)
        return (
            substitute(type_, substitution)
            if isinstance(type_, TypeVar) and type_ in substitution
            else type_
        )
    if isinstance(type_, GenericType):
        return GenericType(
            type_.span,
            type_.base,
            [substitute(arg, substitution) for arg in type_.args],
        )
    if isinstance(type_, FuncType):
        return FuncType(
            type_.span,
            substitute(type_.left, substitution),
            substitute(type_.right, substitution),
        )
    if isinstance(type_, TypeScheme):
        new_sub = {
            var: value
            for var, value in substitution.items()
            if var not in type_.bound_types
        }
        return TypeScheme(substitute(type_.actual_type, new_sub), type_.bound_types)
    raise TypeError(f"{type_} is an invalid subtype of Type, it is {type(type_)}")


def instantiate(type_: Type) -> Type:
    """
    Unwrap the argument if it's a type scheme.

    Parameters
    ----------
    type_: ast_.Type
        The type that will be instantiated if it's an `TypeScheme`.

    Returns
    -------
    ast_.Type
        The instantiated type (generated from the `actual_type` attr).
    """
    if isinstance(type_, TypeScheme):
        substitution = {
            var.value: TypeVar.unknown(type_.span) for var in type_.bound_types
        }
        return substitute(type_.actual_type, substitution)
    return type_


def generalise(type_: Type) -> Type:
    """
    Turn any old type into a type scheme.

    Parameters
    ----------
    type_: ast_.Type
        The type containing free type variables.

    Returns
    -------
    ast_.TypeScheme
        The type scheme with the free type variables quantified over
        it.
    """
    free = find_free_vars(type_)
    if free:
        return TypeScheme(type_, free).fold()
    return type_


def find_free_vars(type_: Type) -> set[TypeVar]:
    """
    Find all the free vars inside of `type_`.

    Parameters
    ----------
    type_: ast_.Type
        The type containing free type variables.

    Returns
    -------
    set[TypeVar]
        All the free type variables found inside of `type_`.
    """
    if isinstance(type_, TypeVar):
        return {type_}
    if isinstance(type_, GenericType):
        return reduce(or_, map(find_free_vars, type_.args), set())
    if isinstance(type_, FuncType):
        return find_free_vars(type_.left) | find_free_vars(type_.right)
    if isinstance(type_, TypeScheme):
        return find_free_vars(type_.actual_type) - type_.bound_types
    raise TypeError(f"{type_} is an invalid subtype of Type, it is {type(type_)}")


class _Inserter(NodeVisitor[typed.TypedASTNode]):
    """
    Annotate the AST with type vars more or less everywhere.

    Notes
    -----
    - The only invariant that this class has is that no AST node which
      has passed through it should have its `type_` attr = `None`.
    """

    def visit_block(self, node: base.Block) -> typed.Block:
        return typed.Block(
            node.span,
            TypeVar.unknown(node.span),
            [expr.visit(self) for expr in node.body()],
        )

    def visit_cond(self, node: base.Cond) -> typed.Cond:
        return typed.Cond(
            node.span,
            TypeVar.unknown(node.span),
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: base.Define) -> typed.Define:
        return typed.Define(
            node.span,
            TypeVar.unknown(node.span),
            node.target.visit(self),
            node.value.visit(self),
            None if node.body is None else node.body.visit(self),
        )

    def visit_func_call(self, node: base.FuncCall) -> typed.FuncCall:
        return typed.FuncCall(
            node.span,
            TypeVar.unknown(node.span),
            node.caller.visit(self),
            node.callee.visit(self),
        )

    def visit_function(self, node: base.Function) -> typed.Function:
        type_ = FuncType(
            node.span,
            TypeVar.unknown(node.param.span),
            TypeVar.unknown(node.body.span),
        )
        return typed.Function(
            node.span,
            type_,
            node.param.visit(self),
            node.body.visit(self),
        )

    def visit_name(self, node: base.Name) -> typed.Name:
        return typed.Name(node.span, TypeVar.unknown(node.span), node.value)

    def visit_scalar(self, node: base.Scalar) -> typed.Scalar:
        return typed.Scalar(
            node.span,
            TypeVar.unknown(node.span),
            node.scalar_type,
            node.value_string,
        )

    def visit_type(self, node: Type) -> Type:
        return node

    def visit_vector(self, node: base.Vector) -> typed.Vector:
        if node.vec_type == base.VectorTypes.TUPLE:
            return typed.Vector(
                node.span,
                TypeVar.unknown(node.span),
                base.VectorTypes.TUPLE,
                (elem.visit(self) for elem in node.elements),
            )

        type_ = GenericType(
            node.span,
            base.Name(node.span, "List"),
            (TypeVar.unknown(node.span),),
        )
        return typed.Vector(
            node.span,
            type_,
            base.VectorTypes.LIST,
            (elem.visit(self) for elem in node.elements),
        )


class _EquationGenerator(NodeVisitor[None]):
    """
    Generate the type equations used during unification.

    Attributes
    ----------
    current_scope: Scope[Type]
        The types of all the variables found in the AST in the
        current lexical scope.
    equations: list[Equation]
        The type equations that have been generated from the AST.

    Notes
    -----
    - This visitor class puts all the equations together in a global
      list since type vars are considered unique unless explicitly
      shared.
    """

    def __init__(self) -> None:
        self.equations: list[tuple[Type, Type]] = []
        self.current_scope: Scope[Type] = Scope(DEFAULT_OPERATOR_TYPES)

    def _push(self, *args: tuple[Type, Type]) -> None:
        self.equations += args

    def visit_block(self, node: typed.Block) -> None:
        self.current_scope = Scope(self.current_scope)
        for expr in (node.first, *node.rest):
            expr.visit(self)

        self._push((node.type_, expr.type_))
        self.current_scope = self.current_scope.parent

    def visit_cond(self, node: typed.Cond) -> None:
        node.pred.visit(self)
        node.cons.visit(self)
        node.else_.visit(self)
        bool_type = GenericType(node.pred.span, base.Name(node.pred.span, "Bool"))
        self._push(
            (node.pred.type_, bool_type),
            (node.type_, node.cons.type_),
            (node.type_, node.else_.type_),
        )

    def visit_define(self, node: typed.Define) -> None:
        node.value.visit(self)
        node.value.type_ = generalise(node.value.type_)
        self._push(
            (node.type_, node.value.type_),
            (node.type_, node.target.type_),
        )
        if node.target in self.current_scope:
            self._push((node.target.type_, self.current_scope[node.target]))

        if node.body is None:
            self.current_scope[node.target] = node.target.type_
        else:
            self.current_scope = Scope(self.current_scope)
            self.current_scope[node.target] = node.target.type_
            node.body.visit(self)
            self.current_scope = self.current_scope.parent

    def visit_function(self, node: typed.Function) -> None:
        self.current_scope = Scope(self.current_scope)
        self.current_scope[node.param] = node.param.type_
        node.body.visit(self)
        self.current_scope = self.current_scope.parent
        actual_type = FuncType(
            node.span,
            node.param.type_,
            node.body.type_,
        )
        self._push((node.type_, actual_type))

    def visit_func_call(self, node: typed.FuncCall) -> None:
        node.caller.visit(self)
        node.callee.visit(self)
        actual_type = FuncType(node.span, node.callee.type_, node.type_)
        self._push((node.caller.type_, actual_type))

    def visit_name(self, node: typed.Name) -> None:
        self._push((node.type_, self.current_scope[node]))

    def visit_scalar(self, node: typed.Scalar) -> None:
        name = {
            base.ScalarTypes.BOOL: "Bool",
            base.ScalarTypes.FLOAT: "Float",
            base.ScalarTypes.INTEGER: "Int",
            base.ScalarTypes.STRING: "String",
        }[node.scalar_type]
        actual_type = GenericType(node.span, base.Name(node.span, name))
        self._push((node.type_, actual_type))

    def visit_type(self, node: Type) -> None:
        return

    def visit_vector(self, node: typed.Vector) -> None:
        if node.vec_type == base.VectorTypes.TUPLE:
            args = []
            for elem in node.elements:
                elem.visit(self)
                args.append(elem.type_)
            actual = (
                GenericType.tuple_type(node.span, args)
                if args
                else GenericType.unit(node.span)
            )

        elif node.vec_type == base.VectorTypes.LIST:
            elem_type = TypeVar.unknown(node.span)
            actual = GenericType(node.span, base.Name(node.span, "List"), (elem_type,))
            for elem in node.elements:
                elem.visit(self)
                self._push((elem.type_, elem_type))

        else:
            raise TypeError(f"Unknown value for base.VectorTypes: {node.vec_type}")

        self._push((node.type_, actual))


class _Substitutor(NodeVisitor[typed.TypedASTNode]):
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
            substitute(node.type_, self.substitution),
            [expr.visit(self) for expr in node.body()],
        )

    def visit_cond(self, node: typed.Cond) -> typed.Cond:
        return typed.Cond(
            node.span,
            substitute(node.type_, self.substitution),
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )

    def visit_define(self, node: typed.Define) -> typed.Define:
        return typed.Define(
            node.span,
            generalise(substitute(node.type_, self.substitution)),
            node.target.visit(self),
            node.value.visit(self),
            None if node.body is None else node.body.visit(self),
        )

    def visit_func_call(self, node: typed.FuncCall) -> typed.FuncCall:
        return typed.FuncCall(
            node.span,
            substitute(node.type_, self.substitution),
            node.caller.visit(self),
            node.callee.visit(self),
        )

    def visit_function(self, node: typed.Function) -> typed.Function:
        return typed.Function(
            node.span,
            generalise(substitute(node.type_, self.substitution)),
            node.param.visit(self),
            node.body.visit(self),
        )

    def visit_name(self, node: typed.Name) -> typed.Name:
        return typed.Name(
            node.span,
            substitute(node.type_, self.substitution),
            node.value,
        )

    def visit_scalar(self, node: typed.Scalar) -> typed.Scalar:
        return node

    def visit_type(self, node: Type) -> Type:
        return node

    def visit_vector(self, node: typed.Vector) -> typed.Vector:
        return typed.Vector(
            node.span,
            substitute(node.type_, self.substitution),
            node.vec_type,
            (elem.visit(self) for elem in node.elements),
        )

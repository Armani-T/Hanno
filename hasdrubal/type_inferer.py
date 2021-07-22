from collections import defaultdict
from functools import reduce
from operator import or_
from typing import Sequence, Union

from errors import TypeMismatchError
from scope import Scope
from visitor import NodeVisitor
import ast_ as ast

Substitution = dict[str, ast.Type]
TypeOrSub = Union[ast.Type, Substitution]


def sort_by_deps(
    exprs: Sequence[ast.ASTNode],
    incoming: dict[ast.ASTNode, ast.Name],
    defintions: dict[ast.Name, ast.Define],
) -> Sequence[ast.ASTNode]:
    """
    Do a topological sort on the exprs inside of `ast_.Block`.

    Parameters
    ----------
    exprs: Sequence[ast_.ASTNode]
        The expressions that are supposed to be sorted.
    incoming: dict[ast_.ASTNode, ast_.Name]
        A mapping of expressions to the names that they require in order to run.
    defintions: dict[ast_.Name, ast_.Define]
        A mapping of names to their definition sites.

    Returns
    -------
    Sequence[ast_.ASTNode]
        The sorted expressions.
    """
    if len(exprs) < 2:
        return exprs

    incoming = {
        expr: [defintions[dep] for dep in deps if dep in defintions]
        for expr, deps in incoming.items()
    }
    incoming_count = {expr: len(incoming[expr]) for expr in exprs}
    outgoing = _generate_outgoing(incoming)
    ready = [node for node, dep_size in incoming_count.items() if dep_size == 0]
    sorted_ = []

    while ready:
        node = ready.pop()
        sorted_.append(node)
        endpoints: Sequence[ast.ASTNode] = outgoing.get(node, ())
        for endpoint in endpoints:
            incoming_count[endpoint] -= 1
            if incoming_count[endpoint] == 0:
                ready.append(endpoint)

    return sorted_


def _generate_outgoing(
    incoming: dict[ast.ASTNode, ast.ASTNode],
) -> dict[ast.ASTNode, set[ast.ASTNode]]:
    results = defaultdict(list)
    for key, value in incoming:
        results[value].append(key)
    return results


def unify(left: ast.Type, right: ast.Type) -> Substitution:
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
    if isinstance(left, ast.TypeVar) or isinstance(right, ast.TypeVar):
        return _unify_type_vars(left, right)
    if isinstance(left, ast.GenericType) and isinstance(right, ast.GenericType):
        return _unify_generics(left, right)
    if isinstance(left, ast.FuncType) and isinstance(right, ast.FuncType):
        return _unify_func_types(left, right)
    if isinstance(left, ast.TypeScheme):
        return unify(instantiate(left), right)
    if isinstance(right, ast.TypeScheme):
        return unify(left, instantiate(right))
    raise TypeMismatchError(left, right)


def _unify_type_vars(left: ast.Type, right: ast.Type) -> Substitution:
    if isinstance(left, ast.TypeVar) and left == right:
        return {}
    if isinstance(left, ast.TypeVar):
        return {left.value: right}
    if isinstance(right, ast.TypeVar):
        return {right.value: left}
    raise TypeMismatchError(left, right)


def _unify_generics(left: ast.GenericType, right: ast.GenericType) -> Substitution:
    if left.base != right.base or len(left.args) != len(right.args):
        raise TypeMismatchError(left, right)

    substitution: Substitution = {}
    for left_arg, right_arg in zip(left.args, right.args):
        result = unify(left_arg, right_arg)
        substitution |= result
    return substitution


def _unify_func_types(left: ast.FuncType, right: ast.FuncType) -> Substitution:
    left_sub = unify(left.left, right.left)
    right_sub = unify(
        substitute(left.right, left_sub),
        substitute(right.right, left_sub),
    )
    return {**left_sub, **right_sub}


def substitute(type_: ast.Type, substitution: Substitution) -> ast.Type:
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
    if isinstance(type_, ast.TypeVar):
        type_ = substitution.get(type_.value, type_)
        return (
            substitute(type_, substitution)
            if isinstance(type_, ast.TypeVar) and type_.value in substitution
            else type_
        )
    if isinstance(type_, ast.GenericType):
        return ast.GenericType(
            type_.span,
            type_.base,
            [substitute(arg, substitution) for arg in type_.args],
        )
    if isinstance(type_, ast.FuncType):
        return ast.FuncType(
            type_.span,
            substitute(type_.left, substitution),
            substitute(type_.right, substitution),
        )
    if isinstance(type_, ast.TypeScheme):
        new_sub = {
            var: value
            for var, value in substitution.items()
            if var not in type_.bound_types
        }
        return ast.TypeScheme(substitute(type_.type_, new_sub), type_.bound_types)
    raise TypeError(f"{type_} is an invalid subtype of ast.Type, it is {type(type_)}")


def instantiate(type_scheme: ast.TypeScheme) -> ast.Type:
    """

    Parameters
    ----------
    type_scheme: ast_.TypeScheme
        The type scheme that will be instantiated.

    Returns
    -------
    ast_.Type
        The instantiated type (generated from the `actual_type` attr).
    """
    substitution = {
        type_.value: ast.TypeVar.unknown(type_scheme.span)
        for type_ in type_scheme.bound_types
    }
    return substitute(type_scheme.type_, substitution)


def generalise(type_: ast.Type) -> ast.TypeScheme:
    """
    Turn any old type into a type scheme.

    Parameters
    ----------
    type_: ast_.Type
        The type containing free type variables.

    Returns
    -------
    ast_.TypeScheme
        The type scheme with the free type variables quanitified over
        it.
    """
    return ast.TypeScheme(type_, find_free_vars(type_))


def find_free_vars(type_: ast.Type) -> set[ast.TypeVar]:
    """
    Find all the free vars inside of `type_`.

    Parameters
    ----------
    type_: ast_.Type
        The type containing free type variables.

    Returns
    -------
    set[ast.TypeVar]
        All the free type variables found inside of `type_`.
    """
    if isinstance(type_, ast.TypeVar):
        return {type_}
    if isinstance(type_, ast.GenericType):
        return reduce(or_, map(find_free_vars, type_.args), set())
    if isinstance(type_, ast.FuncType):
        return find_free_vars(type_.left) | find_free_vars(type_.right)
    if isinstance(type_, ast.TypeScheme):
        return find_free_vars(type_.type_) - type_.bound_types
    raise TypeError(f"{type_} is an invalid subtype of ast.Type, it is {type(type_)}")


class _Reorderer(NodeVisitor[set[ast.Name]]):
    """
    Reorder all blocks within the AST so that all expressions inside
    it are in a position where  all the name sthat they depend on are
    already defined.

    Warnings
    --------
    - This class will change the order of `ast_.Block` nodes.
    - This class can't handle recursive definitions yet.
    """

    def __init__(self) -> None:
        self._definitions: dict[ast.Name, ast.ASTNode] = {}

    def visit_block(self, node: ast.Block) -> set[ast.Name]:
        body = (node.first, *node.rest)
        dep_map: dict[ast.ASTNode, set[ast.Name]] = {}
        total_deps: set[ast.Name] = set()
        prev_definitions = self._definitions
        self._definitions = {}
        for expr in body:
            node_deps = expr.visit(self)
            dep_map[expr] = node_deps
            total_deps |= node_deps

        first, *rest = sort_by_deps(body, dep_map, self._definitions)
        node.first = first
        node.rest = rest
        self._definitions = prev_definitions
        return total_deps

    def visit_cond(self, node: ast.Cond) -> set[ast.Name]:
        body = (node.pred, node.cons, node.else_)
        return reduce(or_, map(self.run, body), set())

    def visit_define(self, node: ast.Define) -> set[ast.Name]:
        self._definitions[node.target] = node
        body_deps = set() if node.body is None else node.body.visit(self)
        return node.value.visit(self) | body_deps

    def visit_func_call(self, node: ast.FuncCall) -> set[ast.Name]:
        return node.caller.visit(self) | node.callee.visit(self)

    def visit_function(self, node: ast.Function) -> set[ast.Name]:
        return node.body.visit(self) - {node.param}

    def visit_name(self, node: ast.Name) -> set[ast.Name]:
        return {node}

    def visit_scalar(self, node: ast.Scalar) -> set[ast.Name]:
        return set()

    def visit_type(self, node: ast.Type) -> set[ast.Name]:
        return set()

    def visit_vector(self, node: ast.Vector) -> set[ast.Name]:
        return reduce(or_, map(self.run, node.elements), set())


class _Inserter(NodeVisitor[ast.ASTNode]):
    """
    Annotate the AST with type vars more or less everywhere.

    Notes
    -----
    - The only invariant that this class has is that no AST node which
      has passed through it should have its `type_` attr = `None`.
    """

    def visit_block(self, node: ast.Block) -> ast.Block:
        body = (node.first, *node.rest)
        new_node = ast.Block(node.span, [expr.visit(self) for expr in body])
        new_node.type_ = ast.TypeVar.unknown(node.span)
        return new_node

    def visit_cond(self, node: ast.Cond) -> ast.Cond:
        new_node = ast.Cond(
            node.span,
            node.pred.visit(self),
            node.cons.visit(self),
            node.else_.visit(self),
        )
        new_node.type_ = ast.TypeVar.unknown(node.span)
        return new_node

    def visit_define(self, node: ast.Define) -> ast.Define:
        new_node = ast.Define(
            node.span,
            node.target.visit(self),
            node.value.visit(self),
            None if node.body is None else node.body.visit(self),
        )
        new_node.type_ = ast.TypeVar.unknown(node.span)
        return new_node

    def visit_func_call(self, node: ast.FuncCall) -> ast.FuncCall:
        new_node = ast.FuncCall(node.caller.visit(self), node.callee.visit(self))
        new_node.type_ = ast.TypeVar.unknown(node.span)
        return new_node

    def visit_function(self, node: ast.Function) -> ast.Function:
        new_node = ast.Function(
            node.span, node.param.visit(self), node.body.visit(self)
        )
        new_node.type_ = ast.FuncType(
            node.span,
            ast.TypeVar.unknown(node.param.span),
            ast.TypeVar.unknown(node.body.span),
        )
        return new_node

    def visit_name(self, node: ast.Name) -> ast.Name:
        node.type_ = ast.TypeVar.unknown(node.span)
        return node

    def visit_scalar(self, node: ast.Scalar) -> ast.Scalar:
        node.type_ = ast.TypeVar.unknown(node.span)
        return node

    def visit_type(self, node: ast.Type) -> ast.Type:
        return node

    def visit_vector(self, node: ast.Vector) -> ast.Vector:
        base_name = {
            ast.VectorTypes.LIST: "List",
            ast.VectorTypes.TUPLE: "Tuple",
        }[node.vec_type]
        new_node = ast.Vector(
            node.span,
            node.vec_type,
            [elem.visit(self) for elem in node.elements],
        )
        new_node.type_ = ast.GenericType(
            node.span,
            ast.Name(node.span, base_name),
            (ast.TypeVar.unknown(node.span),),
        )
        return new_node


class _EquationGenerator(NodeVisitor[None]):
    """
    Generate the type equations used during unification.

    Attributes
    ----------
    current_scope: Scope[ast.Type]
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
        self.equations: list[tuple[ast.Type, ast.Type]] = []
        self.current_scope: Scope[ast.Type] = Scope(None)

    def _push(self, *args: tuple[ast.Type, ast.Type]) -> None:
        self.equations += args

    def visit_block(self, node: ast.Block) -> None:
        self.current_scope = Scope(self.current_scope)
        expr = node.first
        expr.visit(self)
        for expr in node.rest:
            expr.visit(self)

        self._push((node.type_, expr.type_))
        self.current_scope = self.current_scope.parent

    def visit_cond(self, node: ast.Cond) -> None:
        node.pred.visit(self)
        node.cons.visit(self)
        node.else_.visit(self)
        bool_type = ast.GenericType(node.pred.span, ast.Name(node.pred.span, "Bool"))
        self._push(
            (node.pred.type_, bool_type),
            (node.type_, node.cons.type_),
            (node.type_, node.else_.type_),
        )

    def visit_define(self, node: ast.Define) -> None:
        node.value.visit(self)
        self._push(
            (node.type_, node.target.type_),
            (node.type_, node.value.type_),
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

    def visit_function(self, node: ast.Function) -> None:
        self.current_scope = Scope(self.current_scope)
        self.current_scope[node.param] = node.param.type_
        node.body.visit(self)
        self.current_scope = self.current_scope.parent
        actual_type = ast.FuncType(
            node.span,
            node.param.type_,
            node.body.type_,
        )
        self._push((node.type_, actual_type))

    def visit_func_call(self, node: ast.FuncCall) -> None:
        node.caller.visit(self)
        node.callee.visit(self)
        actual_type = ast.FuncType(node.span, node.callee.type_, node.type_)
        self._push((node.caller.type_, actual_type))

    def visit_name(self, node: ast.Name) -> None:
        self._push((node.type_, self.current_scope[node]))

    def visit_scalar(self, node: ast.Scalar) -> None:
        name = {
            ast.ScalarTypes.BOOL: "Bool",
            ast.ScalarTypes.FLOAT: "Float",
            ast.ScalarTypes.INTEGER: "Int",
            ast.ScalarTypes.STRING: "String",
        }[node.scalar_type]
        actual_type = ast.GenericType(node.span, ast.Name(node.span, name))
        self._push((node.type_, actual_type))

    def visit_type(self, node: ast.Type) -> None:
        return

    def visit_vector(self, node: ast.Vector) -> None:
        if node.vec_type == ast.VectorTypes.TUPLE:
            args = []
            for elem in node.elements:
                elem.visit(self)
                args.append(elem.type_)
            actual = ast.GenericType(node.span, ast.Name(node.span, "Tuple"), args)
        elif node.vec_type == ast.VectorTypes.LIST:
            elem_type = ast.TypeVar.unknown(node.span)
            actual = ast.GenericType(
                node.span, ast.Name(node.span, "List"), (elem_type,)
            )
            for elem in node.elements:
                elem.visit(self)
                self._push((elem.type_, elem_type))
        else:
            raise TypeError(f"Unknown value for ast.VectorTypes: {node.vec_type}")

        self._push((node.type_, actual))


class _Substitutor(NodeVisitor[ast.ASTNode]):
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

    def visit_block(self, node: ast.Block) -> ast.Block:
        node.first = node.first.visit(self)
        node.rest = [expr.visit(self) for expr in node.rest]
        node.type_ = substitute(node.type_, self.substitution)
        return node

    def visit_cond(self, node: ast.Cond) -> ast.Cond:
        node.pred = node.pred.visit(self)
        node.cons = node.cons.visit(self)
        node.else_ = node.else_.visit(self)
        node.type_ = substitute(node.type_, self.substitution)
        return node

    def visit_define(self, node: ast.Define) -> ast.Define:
        node.target = node.target.visit(self)
        node.value = node.value.visit(self)
        node.type_ = generalise(substitute(node.type_, self.substitution))
        return node

    def visit_func_call(self, node: ast.FuncCall) -> ast.FuncCall:
        node.caller = node.caller.visit(self)
        node.callee = node.callee.visit(self)
        node.type_ = substitute(node.type_, self.substitution)
        return node

    def visit_function(self, node: ast.Function) -> ast.Function:
        node.param = node.param.visit(self)
        node.body = node.body.visit(self)
        node.type_ = generalise(substitute(node.type_, self.substitution))
        return node

    def visit_name(self, node: ast.Name) -> ast.Name:
        node.type_ = substitute(node.type_, self.substitution)
        return node

    def visit_scalar(self, node: ast.Scalar) -> ast.Scalar:
        node.type_ = substitute(node.type_, self.substitution)
        return node

    def visit_type(self, node: ast.Type) -> ast.Type:
        return node

    def visit_vector(self, node: ast.Vector) -> ast.Vector:
        node.elements = [elem.visit(self) for elem in node.elements]
        node.type_ = substitute(node.type_, self.substitution)
        return node

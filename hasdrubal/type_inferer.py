from functools import reduce
from operator import or_
from typing import Union

from errors import TypeMismatchError
import ast_ as ast

Substitution = dict[str, ast.Type]
TypeOrSub = Union[ast.Type, Substitution]


def unify(left: ast.Type, right: ast.Type) -> Substitution:
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
    substitution = {
        type_.value: ast.TypeVar.unknown(type_scheme.span)
        for type_ in type_scheme.bound_types
    }
    return substitute(type_scheme.type_, substitution)


def generalize(type_: ast.Type) -> ast.TypeScheme:
    return ast.TypeScheme(type_, find_free_vars(type_))


def find_free_vars(type_: TypeOrSub) -> set[ast.TypeVar]:
    if isinstance(type_, ast.TypeVar):
        return {type_}
    if isinstance(type_, ast.GenericType):
        return reduce(or_, map(find_free_vars, type_.args), set())
    if isinstance(type_, ast.FuncType):
        return find_free_vars(type_.left) | find_free_vars(type_.right)
    if isinstance(type_, ast.TypeScheme):
        return find_free_vars(type_.type_) - type_.bound_types
    raise TypeError(f"{type_} is an invalid subtype of ast.Type, it is {type(type_)}")

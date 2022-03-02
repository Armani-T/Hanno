from functools import reduce
from typing import Mapping, Set

from errors import CircularTypeError, TypeMismatchError
from log import logger

from asts.types_ import Type, TypeApply, TypeName, TypeScheme, TypeVar

Substitution = Mapping[TypeVar, Type]


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
    logger.debug("(%r) ~ (%r) => %r", left, right, result)
    return result


def _unify(left: Type, right: Type) -> Substitution:
    left, right = instantiate(left), instantiate(right)
    if isinstance(left, TypeVar):
        if isinstance(right, TypeVar) and left.value == right.value:
            return {}
        if left in right:
            logger.fatal("Circularity detected in (%r) ~ (%r)", left, right)
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
    logger.fatal("Cannot unify: (%r) ~ (%r)", left, right)
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
        return {key: substitute(value, full_sub) for key, value in full_sub.items()}
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
        return substitute(
            type_.actual_type,
            {var: TypeVar.unknown(type_.span) for var in type_.bound_types},
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
    return fold_schemes(TypeScheme(type_, free_vars)) if free_vars else type_


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


def fold_schemes(scheme: TypeScheme) -> TypeScheme:
    """Merge several nested type schemes into a single one."""
    if isinstance(scheme.actual_type, TypeScheme):
        inner = fold_schemes(scheme.actual_type)
        return TypeScheme(inner.actual_type, inner.bound_types | scheme.bound_types)
    return scheme


def substitute(type_: Type, substitution: Substitution) -> Type:
    """
    Replace free type vars in the object with the types in
    `substitution`.

    Parameters
    ----------
    substitution: Substitution
        The mapping to used to replace the free type vars.

    Returns
    -------
    Type
        The same object but without any free type variables.
    """
    if isinstance(type_, TypeName):
        return type_
    if isinstance(type_, TypeVar):
        while isinstance(type_, TypeVar) and type_ in substitution:
            type_ = substitution.get(type_, type_)
        return type_
    if isinstance(type_, TypeApply):
        return TypeApply(
            type_.span,
            substitute(type_.caller, substitution),
            substitute(type_.callee, substitution),
        )
    if isinstance(type_, TypeScheme):
        actual_sub = {
            var: value
            for var, value in substitution.items()
            if var not in type_.bound_types
        }
        return TypeScheme(substitute(type_.actual_type, actual_sub), type_.bound_types)
    assert False

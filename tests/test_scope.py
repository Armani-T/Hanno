# pylint: disable=C0116, W0212
from pytest import raises

from context import base, errors, scope


def test_scope_down():
    parent = scope.Scope(None)
    name = base.Name((1, 2), "z")
    parent[name] = base.Scalar((5, 9), False)
    child = parent.down()

    assert child is not parent
    assert name in child
    assert name in parent


def test_scope_up():
    sample_parent = scope.Scope(None)
    sample = scope.Scope(sample_parent)
    result = sample.up()
    assert result is not sample
    assert result is sample._parent


def test_scope_depth_with_undefined_name():
    name = base.Name((0, 1), "<+>")
    assert scope.OPERATOR_TYPES.depth(name) == -1


def test_scope_depth_with_no_nesting():
    name = base.Name((0, 1), "+")
    assert scope.OPERATOR_TYPES.depth(name) == 0


def test_scope_depth_with_nested_2():
    parent = scope.Scope(None)
    name = base.Name((0, 6), "my_var")
    parent[name] = base.Scalar((10, 12), 42)
    child = parent.down()
    assert child.depth(name) == 1


def test_scope_depth_with_nested_5():
    parent = scope.Scope(None)
    name = base.Name((0, 6), "my_var")
    parent[name] = base.Scalar((10, 12), 42)
    child = parent
    for _ in range(5):
        child = child.down()

    assert child.depth(name) == 5


def test_scope_depth_with_shadowing():
    parent = scope.Scope(None)
    upper_name = base.Name((0, 6), "my_var")
    parent[upper_name] = base.Scalar((10, 12), 42)
    child = parent
    for _ in range(4):
        child = child.down()

    lower_name = base.Name((238, 244), "my_var")
    child[lower_name] = base.Scalar((10, 12), 67)
    assert child.depth(upper_name) == 4
    assert child.depth(lower_name) == 4

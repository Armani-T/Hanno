# pylint: disable=C0116, W0212
from pytest import raises

from context import base, errors, scope

SAMPLE_SCOPE = scope.Scope(scope.DEFAULT_OPERATOR_TYPES)


def test_scope_down():
    parent = scope.Scope(None)
    name = base.Name((1, 2), "z")
    parent[name] = base.Scalar((5, 9), False)
    child = parent.down()

    assert child is not parent
    assert name in child
    assert name in parent


def test_scope_up_failure():
    with raises(errors.FatalInternalError):
        sample = scope.Scope(None)
        sample.up()


def test_scope_up_success():
    sample_parent = scope.Scope(None)
    sample = scope.Scope(sample_parent)
    result = sample.up()
    assert result is not sample
    assert result is sample._parent

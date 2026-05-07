from pytest import mark, raises

from context import base, errors, scope


@mark.type_inference
def test_scope_down():
    parent = scope.Scope(None)
    name = base.Name((1, 2), "z")
    parent[name] = base.Scalar((5, 9), False)
    child = parent.down()

    assert child is not parent
    assert name in child
    assert name in parent


@mark.type_inference
def test_scope_up():
    sample_parent = scope.Scope(None)
    sample = scope.Scope(sample_parent)
    result = sample.up()
    assert result is not sample
    assert result is sample._parent


@mark.type_inference
def test_scope_depth_with_undefined_name():
    name = base.Name((0, 1), "<+>")
    assert scope.OPERATOR_TYPES.depth(name) == -1


@mark.type_inference
def test_scope_depth_with_no_nesting():
    name = base.Name((0, 1), "+")
    assert scope.OPERATOR_TYPES.depth(name) == 0


@mark.type_inference
def test_scope_depth_with_nesting_2():
    parent = scope.Scope(None)
    name = base.Name((0, 6), "my_var")
    parent[name] = base.Scalar((10, 12), 42)
    child = parent.down()
    assert child.depth(name) == 1


@mark.type_inference
def test_scope_depth_with_nested_5():
    parent = scope.Scope(None)
    name = base.Name((0, 6), "my_var")
    parent[name] = base.Scalar((10, 12), 42)
    child = parent
    for _ in range(5):
        child = child.down()

    assert child.depth(name) == 5


@mark.type_inference
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


@mark.type_inference
def test_scope_raises_undefined_name_error():
    with raises(errors.UndefinedNameError):
        scope_ = scope.Scope(None)
        name = base.Name((0, 0), "x")
        scope_[name]


@mark.type_inference
def test_scope_contains():
    upper_scope = scope.Scope(None)
    middle_scope = scope.Scope(upper_scope)
    lower_scope = scope.Scope(middle_scope)
    name_x, name_y = base.Name((0, 0), "x"), base.Name((0, 0), "y")
    upper_scope[name_x] = base.Scalar((0, 0), 3)
    middle_scope[name_y] = base.Scalar((0, 0), 4)
    assert name_x in lower_scope and name_y in lower_scope
    assert name_x in middle_scope and name_y in middle_scope
    assert name_x in upper_scope and name_y not in upper_scope

    del lower_scope[name_x]
    del middle_scope[name_y]

    assert name_x not in lower_scope and name_y not in lower_scope
    assert name_x not in middle_scope and name_y not in middle_scope


@mark.type_inference
def test_scope_bool():
    scope_1 = scope.Scope(None)
    scope_2 = scope.Scope(None)
    scope_1[base.Name((0, 0), "x")] = base.Scalar((0, 0), 1)
    assert bool(scope_1)
    assert not bool(scope_2)


@mark.type_inference
def test_scope_iter():
    scope_ = scope.Scope(None)
    scope_[base.Name((0, 0), "x")] = base.Scalar((0, 0), 1)
    scope_[base.Name((0, 0), "y")] = base.Scalar((0, 0), 2)
    expected_index = 1
    for actual_index, _ in enumerate(scope_):
        ...

    assert expected_index == actual_index


@mark.type_inference
def test_scope_get():
    scope_ = scope.Scope(None)
    scope_[base.Name((0, 0), "x")] = base.Scalar((0, 0), 1)
    assert base.Scalar((0, 0), 1) == scope_.get(base.Name((0, 0), "x"))


@mark.type_inference
def test_scope_get_with_absent_name():
    scope_ = scope.Scope(None)
    scope_[base.Name((0, 0), "x")] = base.Scalar((0, 0), 1)
    assert scope_.get(base.Name((0, 0), "y")) is None


@mark.type_inference
def test_scope_get_with_parent():
    parent_scope = scope.Scope(None)
    parent_scope[base.Name((0, 0), "x")] = base.Scalar((0, 0), 1)
    child_scope = scope.Scope(parent_scope)
    assert base.Scalar((0, 0), 1) == child_scope.get(base.Name((0, 0), "x"))

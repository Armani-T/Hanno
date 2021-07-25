from pytest import mark, raises

from context import ast, errors, type_inferer

span = (0, 0)
# NOTE: This is supposed to be a dummy value to pass into constructors
#   from the `ast_` module.
int_type = ast.GenericType(span, ast.Name(span, "Int"))
bool_type = ast.GenericType(span, ast.Name(span, "Bool"))


@mark.type_inference
@mark.parametrize(
    "left,right,expected_names",
    (
        (
            ast.TypeVar(span, "x"),
            ast.TypeVar(span, "x"),
            {},
        ),
        (
            ast.TypeVar(span, "a"),
            bool_type,
            {"a": ast.GenericType},
        ),
        (
            ast.FuncType(span, ast.TypeVar(span, "bar"), int_type),
            ast.TypeVar(span, "foo"),
            {"foo": ast.FuncType},
        ),
        (
            ast.GenericType(span, ast.Name(span, "List"), (ast.TypeVar(span, "a"),)),
            ast.GenericType(span, ast.Name(span, "List"), (int_type,)),
            {"a": ast.GenericType},
        ),
        (
            ast.FuncType(span, ast.TypeVar(span, "a"), ast.TypeVar(span, "b")),
            ast.FuncType(span, bool_type, int_type),
            {"a": ast.GenericType, "b": ast.GenericType},
        ),
    ),
)
def test_unify(left, right, expected_names):
    result = type_inferer.unify(left, right)
    for name, expected_type in expected_names.items():
        assert name in result
        assert isinstance(result[name], expected_type)


@mark.type_inference
@mark.parametrize(
    "left,right",
    (
        (int_type, bool_type),
        (
            ast.FuncType(span, int_type, bool_type),
            ast.FuncType(span, bool_type, int_type),
        ),
    ),
)
def test_unify_raises_type_mismatch_error(left, right):
    with raises(errors.TypeMismatchError):
        type_inferer.unify(left, right)


@mark.type_inference
@mark.parametrize(
    "type_,sub,expected",
    (
        (
            ast.TypeVar(span, "a"),
            {"a": ast.TypeVar(span, "b"), "b": ast.TypeVar(span, "c"), "c": bool_type},
            bool_type,
        ),
        (
            ast.FuncType(
                span,
                ast.GenericType(
                    span, ast.Name(span, "List"), (ast.TypeVar(span, "x"),)
                ),
                int_type,
            ),
            {"x": int_type},
            ast.FuncType(
                span,
                ast.GenericType(span, ast.Name(span, "List"), (int_type,)),
                int_type,
            ),
        ),
        (
            ast.TypeScheme(
                ast.FuncType(
                    span,
                    ast.FuncType(span, ast.TypeVar(span, "z"), ast.TypeVar(span, "y")),
                    ast.TypeVar(span, "x"),
                ),
                {ast.TypeVar(span, "x"), ast.TypeVar(span, "y")},
            ),
            {"z": int_type},
            ast.TypeScheme(
                ast.FuncType(
                    span,
                    ast.FuncType(span, int_type, ast.TypeVar(span, "y")),
                    ast.TypeVar(span, "x"),
                ),
                {ast.TypeVar(span, "x"), ast.TypeVar(span, "y")},
            ),
        ),
    ),
)
def test_substitute(type_, sub, expected):
    actual = type_inferer.substitute(type_, sub)
    assert actual == expected


@mark.type_inference
@mark.parametrize(
    "sub,expected",
    (
        ({}, {}),
        (
            {"a": ast.TypeVar(span, "b"), "b": int_type},
            {"a": int_type, "b": int_type},
        ),
        (
            {"a": None, "b": bool_type},
            {"b": bool_type},
        ),
    )
)
def test_self_substitute(sub, expected):
    actual = type_inferer._self_substitute(sub)
    assert actual == expected


@mark.type_inference
def test_instantiate():
    type_scheme = ast.TypeScheme(
        ast.FuncType(span, ast.TypeVar(span, "foo"), int_type),
        {ast.TypeVar(span, "foo")},
    )
    expected = ast.FuncType(span, ast.TypeVar(span, "foo"), int_type)
    result = type_inferer.instantiate(type_scheme)
    assert not isinstance(result, ast.TypeScheme)
    # noinspection PyUnresolvedReferences
    assert result.right == expected.right


@mark.type_inference
@mark.parametrize(
    "type_,type_vars",
    (
        (bool_type, 0),
        (ast.TypeVar(span, "f"), 1),
        (ast.GenericType(span, ast.Name(span, "List"), (ast.TypeVar(span, "a"),)), 1),
        (ast.FuncType(span, ast.TypeVar(span, "x"), ast.TypeVar(span, "y")), 2),
    )
)
def test_generalise(type_, type_vars):
    actual = type_inferer.generalise(type_)
    if type_vars:
        assert isinstance(actual, ast.TypeScheme)
        assert isinstance(actual.actual_type, type(type_))
        assert len(actual.bound_types) == type_vars
    else:
        assert not isinstance(actual, ast.TypeScheme)


@mark.type_inference
@mark.parametrize(
    "type_,expected",
    (
        (
            ast.TypeVar(span, "foo"),
            {"foo"},
        ),
        (
            int_type,
            set(),
        ),
        (
            ast.GenericType(span, ast.Name(span, "Set"), (ast.TypeVar(span, "x"),)),
            {"x"},
        ),
        (
            ast.FuncType(span, ast.TypeVar(span, "a"), ast.TypeVar(span, "b")),
            {"a", "b"},
        ),
    ),
)
def test_find_free_vars(type_, expected):
    result = type_inferer.find_free_vars(type_)
    actual = {var.value for var in result}
    assert actual == expected

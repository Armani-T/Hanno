from pytest import mark

from context import ast, type_inferer

span = (0, 0)
# NOTE: This is supposed to be a dummy value to pass into consturctors
#   from the `ast_` module.
int_type = ast.GenericType(span, ast.Name(span, "Int"))
bool_type = ast.GenericType(span, ast.Name(span, "Bool"))


@mark.type_inference
@mark.parametrize(
    "left,right,expected_names",
    (
        (
            ast.TypeVar(span, "a"),
            bool_type,
            {"a": ast.GenericType},
        ),
        (
            ast.TypeVar(span, "foo"),
            ast.FuncType(span, ast.TypeVar(span, "bar"), int_type),
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
def test_instantiate():
    type_scheme = ast.TypeScheme(
        ast.FuncType(span, ast.TypeVar(span, "foo"), int_type),
        (ast.TypeVar(span, "foo"),),
    )
    expected = ast.FuncType(span, ast.TypeVar(span, "foo"), int_type)
    result = type_inferer.instantiate(type_scheme)
    assert not isinstance(result, ast.TypeScheme)
    # noinspection PyUnresolvedReferences
    assert result.right == expected.right


@mark.type_inference
@mark.parametrize(
    "type_,expected",
    (
        (
            ast.TypeScheme(ast.TypeVar(span, "foo"), {ast.TypeVar(span, "foo")}),
            set(),
        ),
        (
            ast.TypeScheme(
                ast.FuncType(span, ast.TypeVar(span, "x"), int_type),
                {ast.TypeVar(span, "x")},
            ),
            {"x"},
        ),
        (
            ast.TypeScheme(
                ast.FuncType(span, ast.TypeVar(span, "a"), ast.TypeVar(span, "b")),
                {ast.TypeVar(span, "a"), ast.TypeVar(span, "b")},
            ),
            {"a", "b"},
        ),
        (
            ast.TypeScheme(
                ast.FuncType(span, int_type, int_type),
                {ast.TypeVar(span, "z")},
            ),
            {"z"},
        ),
    ),
)
def test_find_free_vars(type_, expected):
    result = type_inferer.find_free_vars(type_)
    assert result == expected

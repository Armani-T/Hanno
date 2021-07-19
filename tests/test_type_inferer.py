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
            ast.FuncType(span, ast.TypeVar(span, "a"), ast.TypeVar(span, "a")),
            ast.FuncType(span, ast.TypeVar(span, "a"), bool_type),
            {"a": ast.GenericType},
        ),
        (
            ast.FuncType(span, ast.TypeVar(span, "a"), ast.TypeVar(span, "b")),
            ast.FuncType(span, bool_type, int_type),
            {"a": ast.GenericType, "b": ast.GenericType},
        )
    ),
)
def test_unify(left, right, expected_names):
    result = type_inferer.unify((left, right))
    for name, expected_type in expected_names.items():
        assert name in result
        assert isinstance(result[name], expected_type)

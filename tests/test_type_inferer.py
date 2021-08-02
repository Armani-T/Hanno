from pytest import mark, raises

from context import base, errors, type_inferer, types

span = (0, 0)
# NOTE: This is supposed to be a dummy value to pass to AST constructors
int_type = types.GenericType(span, base.Name(span, "Int"))
bool_type = types.GenericType(span, base.Name(span, "Bool"))


@mark.integration
@mark.type_inference
@mark.parametrize(
    "untyped_ast,expected_type",
    (
        (
            base.Scalar(span, base.ScalarTypes.INTEGER, "1"),
            int_type,
        ),
        (
            base.Function(span, base.Name(span, "x"), base.Name(span, "x")),
            types.TypeScheme(
                types.FuncType(
                    span, types.TypeVar(span, "a"), types.TypeVar(span, "a")
                ),
                {types.TypeVar(span, "a")},
                ),
        ),
        (
            base.Define(
                span,
                base.Name(span, "id"),
                base.Function(span, base.Name(span, "x"), base.Name(span, "x")),
            ),
            types.TypeScheme(
                types.FuncType(
                    span, types.TypeVar(span, "a"), types.TypeVar(span, "a")
                ),
                {types.TypeVar(span, "a")},
            ),
        ),
    ),
)
def test_infer_types(untyped_ast, expected_type):
    typed_ast = type_inferer.infer_types(untyped_ast)
    assert typed_ast.type_ == expected_type


@mark.type_inference
@mark.parametrize(
    "left,right,expected_names",
    (
        (
            types.TypeVar(span, "x"),
            types.TypeVar(span, "x"),
            {},
        ),
        (
            types.TypeVar(span, "a"),
            bool_type,
            {"a": types.GenericType},
        ),
        (
            types.FuncType(span, types.TypeVar(span, "bar"), int_type),
            types.TypeVar(span, "foo"),
            {"foo": types.FuncType},
        ),
        (
            types.GenericType(
                span, base.Name(span, "List"), (types.TypeVar(span, "a"),)
            ),
            types.GenericType(span, base.Name(span, "List"), (int_type,)),
            {"a": types.GenericType},
        ),
        (
            types.FuncType(span, types.TypeVar(span, "a"), types.TypeVar(span, "b")),
            types.FuncType(span, bool_type, int_type),
            {"a": types.GenericType, "b": types.GenericType},
        ),
    ),
)
def test_unify(left, right, expected_names):
    substitution = type_inferer.unify(left, right)
    substitution = {key.value: value for key, value in substitution.items()}
    for name, expected_type in expected_names.items():
        assert name in substitution
        assert isinstance(substitution[name], expected_type)


@mark.type_inference
@mark.parametrize(
    "left,right",
    (
        (int_type, bool_type),
        (
            types.FuncType(span, int_type, bool_type),
            types.FuncType(span, bool_type, int_type),
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
            types.TypeVar(span, "a"),
            {
                "a": types.TypeVar(span, "b"),
                "b": types.TypeVar(span, "c"),
                "c": bool_type,
            },
            bool_type,
        ),
        (
            types.FuncType(
                span,
                types.GenericType(
                    span, base.Name(span, "List"), (types.TypeVar(span, "x"),)
                ),
                int_type,
            ),
            {"x": int_type},
            types.FuncType(
                span,
                types.GenericType(span, base.Name(span, "List"), (int_type,)),
                int_type,
            ),
        ),
        (
            types.TypeScheme(
                types.FuncType(
                    span,
                    types.FuncType(
                        span, types.TypeVar(span, "z"), types.TypeVar(span, "y")
                    ),
                    types.TypeVar(span, "x"),
                ),
                {types.TypeVar(span, "x"), types.TypeVar(span, "y")},
            ),
            {"z": int_type},
            types.TypeScheme(
                types.FuncType(
                    span,
                    types.FuncType(span, int_type, types.TypeVar(span, "y")),
                    types.TypeVar(span, "x"),
                ),
                {types.TypeVar(span, "x"), types.TypeVar(span, "y")},
            ),
        ),
    ),
)
def test_substitute(type_, sub, expected):
    actual_sub = {types.TypeVar(span, key): value for key, value in sub.items()}
    actual = type_inferer.substitute(type_, actual_sub)
    assert actual == expected


@mark.type_inference
@mark.parametrize(
    "sub,expected",
    (
        ({}, {}),
        (
            {
                types.TypeVar(span, "a"): types.TypeVar(span, "b"),
                types.TypeVar(span, "b"): int_type,
            },
            {types.TypeVar(span, "a"): int_type, types.TypeVar(span, "b"): int_type},
        ),
        (
            {types.TypeVar(span, "p"): None, types.TypeVar(span, "x"): bool_type},
            {types.TypeVar(span, "x"): bool_type},
        ),
    ),
)
def test_self_substitute(sub, expected):
    actual = type_inferer.self_substitute(sub)
    assert actual == expected


@mark.type_inference
def test_instantiate():
    type_scheme = types.TypeScheme(
        types.FuncType(span, types.TypeVar(span, "foo"), int_type),
        {types.TypeVar(span, "foo")},
    )
    expected = types.FuncType(span, types.TypeVar(span, "foo"), int_type)
    result = type_inferer.instantiate(type_scheme)
    assert not isinstance(result, types.TypeScheme)
    # noinspection PyUnresolvedReferences
    assert result.right == expected.right


@mark.type_inference
@mark.parametrize(
    "type_,type_vars",
    (
        (bool_type, 0),
        (types.TypeVar(span, "f"), 1),
        (
            types.GenericType(
                span, base.Name(span, "List"), (types.TypeVar(span, "a"),)
            ),
            1,
        ),
        (types.FuncType(span, types.TypeVar(span, "x"), types.TypeVar(span, "y")), 2),
    ),
)
def test_generalise(type_, type_vars):
    actual = type_inferer.generalise(type_)
    if type_vars:
        assert isinstance(actual, types.TypeScheme)
        assert isinstance(actual.actual_type, type(type_))
        assert len(actual.bound_types) == type_vars
    else:
        assert not isinstance(actual, types.TypeScheme)


@mark.type_inference
@mark.parametrize(
    "type_,expected",
    (
        (
            types.TypeVar(span, "foo"),
            {"foo"},
        ),
        (
            int_type,
            set(),
        ),
        (
            types.GenericType(
                span, base.Name(span, "Set"), (types.TypeVar(span, "x"),)
            ),
            {"x"},
        ),
        (
            types.FuncType(span, types.TypeVar(span, "a"), types.TypeVar(span, "b")),
            {"a", "b"},
        ),
        (
            types.TypeScheme(
                types.FuncType(
                    span,
                    types.TypeVar(span, "x"),
                    types.FuncType(
                        span, types.TypeVar(span, "y"), types.TypeVar(span, "z")
                    ),
                ),
                {types.TypeVar(span, "z")},
            ),
            {"x", "y"},
        ),
    ),
)
def test_find_free_vars(type_, expected):
    result = type_inferer.find_free_vars(type_)
    actual = {var.value for var in result}
    assert actual == expected

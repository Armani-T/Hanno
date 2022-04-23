# pylint: disable=C0116
from pytest import mark, raises

from context import base, errors, lex, parse, types, type_inference

span = (0, 0)
# NOTE: This is a dummy value to pass into to AST constructors.

float_type = types.TypeName(span, "Float")
int_type = types.TypeName(span, "Int")
bool_type = types.TypeName(span, "Bool")

_prepare = lambda source: parse.parse(lex.TokenStream(lex.infer_eols(lex.lex(source))))


@mark.integration
@mark.type_inference
@mark.parametrize(
    "source,expected_type",
    (
        ("()", types.TypeName.unit(span)),
        ("-12", int_type),
        (
            "[]",
            types.TypeApply(
                span, types.TypeName(span, "List"), types.TypeVar(span, "a")
            ),
        ),
        (
            "let eq (a, b) = (a = b)",
            types.TypeScheme(
                types.TypeApply.func(
                    span,
                    types.TypeApply.pair(
                        span, types.TypeVar(span, "a"), types.TypeVar(span, "a")
                    ),
                    bool_type,
                ),
                {types.TypeVar(span, "a")},
            ),
        ),
        ("let plus_one x = x + 1", types.TypeApply.func(span, int_type, int_type)),
        (
            "let negate_float x = 0.0 - x",
            types.TypeApply.func(span, float_type, float_type),
        ),
        (
            "\\x -> x",
            types.TypeApply.func(
                span, types.TypeVar(span, "a"), types.TypeVar(span, "a")
            ),
        ),
        ("let base = 12\nlet sub = 3\nbase * sub", int_type),
        (
            "let return x = x\n(return 1, return True, return 6.521)",
            types.TypeApply.tuple_(span, (int_type, bool_type, float_type)),
        ),
        (
            ("let map_add f, x, y = f x + f y\n" "map_add (\\x -> x ^ 2, 3, 5)"),
            int_type,
        ),
    ),
)
def test_infer_types(source, expected_type):
    untyped_ast = _prepare(source)
    typed_ast = type_inference.infer_types(untyped_ast)
    actual_type = typed_ast.type_
    assert expected_type == actual_type


@mark.type_inference
@mark.parametrize(
    "left,right,expected",
    (
        (
            types.TypeVar(span, "x"),
            types.TypeVar(span, "x"),
            {},
        ),
        (
            types.TypeVar(span, "a"),
            bool_type,
            {types.TypeVar(span, "a"): bool_type},
        ),
        (
            types.TypeApply.func(span, types.TypeVar(span, "bar"), int_type),
            types.TypeVar(span, "foo"),
            {
                types.TypeVar(span, "foo"): types.TypeApply.func(
                    span, types.TypeVar(span, "bar"), int_type
                )
            },
        ),
        (
            types.TypeApply(
                span, types.TypeName(span, "List"), types.TypeVar(span, "a")
            ),
            types.TypeApply(span, types.TypeName(span, "List"), bool_type),
            {types.TypeVar(span, "a"): bool_type},
        ),
        (
            types.TypeApply.func(
                span, types.TypeVar(span, "a"), types.TypeVar(span, "b")
            ),
            types.TypeApply.func(span, bool_type, int_type),
            {types.TypeVar(span, "a"): bool_type, types.TypeVar(span, "b"): int_type},
        ),
    ),
)
def test_unify(left, right, expected):
    actual = type_inference.unify(left, right)
    assert expected == actual


@mark.type_inference
@mark.parametrize(
    "left,right",
    (
        (int_type, bool_type),
        (
            types.TypeApply.func(span, int_type, bool_type),
            types.TypeApply.func(span, bool_type, int_type),
        ),
    ),
)
def test_unify_raises_type_mismatch_error(left, right):
    with raises(errors.TypeMismatchError):
        type_inference.unify(left, right)


@mark.type_inference
@mark.parametrize(
    "source",
    (
        "let Ω = (\\x -> x x) (\\x -> x x)",
        "let Y(func) = \\x -> (func(x(x)))(func(x(x)))",
    ),
)
def test_unify_raises_circular_type_error(source):
    with raises(errors.CircularTypeError):
        untyped_ast = _prepare(source)
        type_inference.infer_types(untyped_ast)


@mark.type_inference
@mark.parametrize(
    "type_,sub,expected",
    (
        (
            types.TypeVar(span, "a"),
            {
                types.TypeVar(span, "a"): types.TypeVar(span, "b"),
                types.TypeVar(span, "b"): types.TypeVar(span, "c"),
                types.TypeVar(span, "c"): bool_type,
            },
            bool_type,
        ),
        (
            types.TypeApply.func(
                span,
                types.TypeApply(
                    span,
                    types.TypeName(span, "List"),
                    types.TypeVar(span, "x"),
                ),
                types.TypeVar(span, "x"),
            ),
            {types.TypeVar(span, "x"): int_type},
            types.TypeApply.func(
                span,
                types.TypeApply(span, types.TypeName(span, "List"), int_type),
                int_type,
            ),
        ),
        (
            types.TypeScheme(
                types.TypeApply.func(
                    span,
                    types.TypeApply.func(
                        span, types.TypeVar(span, "x"), types.TypeVar(span, "y")
                    ),
                    types.TypeVar(span, "z"),
                ),
                {types.TypeVar(span, "x"), types.TypeVar(span, "y")},
            ),
            {types.TypeVar(span, "z"): int_type},
            types.TypeScheme(
                types.TypeApply.func(
                    span,
                    types.TypeApply.func(
                        span, types.TypeVar(span, "x"), types.TypeVar(span, "y")
                    ),
                    int_type,
                ),
                {types.TypeVar(span, "x"), types.TypeVar(span, "y")},
            ),
        ),
    ),
)
def test_substitute(type_, sub, expected):
    assert expected == type_inference.substitute(type_, sub)


@mark.type_inference
@mark.parametrize(
    "type_,expected",
    (
        (
            bool_type,
            bool_type,
        ),
        (
            types.TypeApply.func(span, int_type, bool_type),
            types.TypeApply.func(span, int_type, bool_type),
        ),
        (
            # NOTE: Strictly speaking, this type isn't even allowed in
            # the language type system. I just threw it in to make the
            # tests more complete.
            types.TypeApply.func(
                span,
                types.TypeScheme(
                    types.TypeApply.func(
                        span, types.TypeVar(span, "x"), types.TypeVar(span, "x")
                    ),
                    {types.TypeVar(span, "x")},
                ),
                bool_type,
            ),
            types.TypeApply.func(
                span,
                types.TypeScheme(
                    types.TypeApply.func(
                        span, types.TypeVar(span, "y"), types.TypeVar(span, "y")
                    ),
                    {types.TypeVar(span, "y")},
                ),
                bool_type,
            ),
        ),
        (
            types.TypeScheme(
                types.TypeApply.func(span, types.TypeVar(span, "x"), float_type),
                {types.TypeVar(span, "x")},
            ),
            types.TypeApply.func(span, types.TypeVar.unknown(span), float_type),
        ),
        (
            types.TypeScheme(
                types.TypeApply.func(
                    span, types.TypeVar(span, "x"), types.TypeVar(span, "x")
                ),
                {types.TypeVar(span, "x")},
            ),
            types.TypeApply.func(
                span, types.TypeVar(span, "a"), types.TypeVar(span, "a")
            ),
        ),
    ),
)
def test_instantiate(type_, expected):
    actual = type_inference.instantiate(type_)
    assert not isinstance(actual, types.TypeScheme)
    assert expected == actual


@mark.type_inference
@mark.parametrize(
    "type_,type_vars",
    (
        (bool_type, 0),
        (types.TypeVar(span, "f"), 1),
        (
            types.TypeApply(
                span, types.TypeName(span, "List"), types.TypeVar(span, "a")
            ),
            1,
        ),
        (
            types.TypeApply.func(
                span, types.TypeVar(span, "x"), types.TypeVar(span, "y")
            ),
            2,
        ),
    ),
)
def test_generalise(type_, type_vars):
    actual = type_inference.generalise(type_)
    if type_vars:
        assert isinstance(actual, types.TypeScheme)
        assert not isinstance(actual.actual_type, types.TypeScheme)
        assert len(actual.bound_types) == type_vars
    else:
        assert not isinstance(actual, types.TypeScheme)


@mark.type_inference
@mark.parametrize(
    "type_,expected",
    (
        (types.TypeVar(span, "foo"), {"foo"}),
        (int_type, set()),
        (
            types.TypeApply(
                span, types.TypeName(span, "Set"), types.TypeVar(span, "x")
            ),
            {"x"},
        ),
        (
            types.TypeApply.func(
                span, types.TypeVar(span, "a"), types.TypeVar(span, "b")
            ),
            {"a", "b"},
        ),
        (
            types.TypeScheme(
                types.TypeApply.func(
                    span,
                    types.TypeVar(span, "x"),
                    types.TypeApply.func(
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
    result = type_inference.find_free_vars(type_)
    actual = {var.value for var in result}
    assert expected == actual

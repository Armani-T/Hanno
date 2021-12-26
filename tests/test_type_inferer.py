# pylint: disable=C0116
from pytest import mark, raises

from context import base, errors, lex, parse, type_inferer, types

span = (0, 0)
# NOTE: This is a dummy value to pass into to AST constructors.
float_type = types.TypeName(span, "Float")
int_type = types.TypeName(span, "Int")
bool_type = types.TypeName(span, "Bool")


def _prepare(source: str, do_inference: bool) -> base.ASTNode:
    """
    Prepare a `TokenStream` for the lexer to use from a source string.
    """
    identity = lambda string: string
    infer = lex.infer_eols if do_inference else identity
    return parse.parse(lex.TokenStream(infer(lex.lex(source))))


@mark.integration
@mark.type_inference
@mark.parametrize(
    "source,do_inference,expected_type",
    (
        ("-12", False, int_type),
        ("let base = 12\nlet sub = 3\nbase * sub", True, int_type),
        ("()", False, types.TypeName.unit(span)),
        (
            "[]",
            False,
            types.TypeApply(
                span, types.TypeName(span, "List"), types.TypeVar.unknown(span)
            ),
        ),
        (
            "let eq(a, b) = (a = b)",
            False,
            types.TypeScheme(
                types.TypeApply.func(
                    span,
                    types.TypeVar(span, "x"),
                    types.TypeApply.func(
                        span,
                        types.TypeVar(span, "x"),
                        bool_type,
                    ),
                ),
                {types.TypeVar(span, "x")},
            ),
        ),
        (
            "let plus_one(x) = x + 1",
            False,
            types.TypeApply.func(span, int_type, int_type),
        ),
        (
            "let negate_float(x) = 0.0 - x",
            False,
            types.TypeApply.func(span, float_type, float_type),
        ),
        (
            "\\x -> x",
            False,
            types.TypeScheme(
                types.TypeApply.func(
                    span, types.TypeVar(span, "a"), types.TypeVar(span, "a")
                ),
                {types.TypeVar(span, "a")},
            ),
        ),
        (
            "let return(x) = x",
            False,
            types.TypeScheme(
                types.TypeApply.func(
                    span, types.TypeVar(span, "a"), types.TypeVar(span, "a")
                ),
                {types.TypeVar(span, "a")},
            ),
        ),
        (
            "let Y(func) :=\nlet inner(x) = func(x(x))\ninner(inner)\nend\n",
            True,
            types.TypeScheme(
                types.TypeApply.func(
                    span,
                    types.TypeApply.func(
                        span,
                        types.TypeVar(span, "a"),
                        types.TypeVar(span, "a"),
                    ),
                    types.TypeVar(span, "a"),
                ),
                {types.TypeVar(span, "a")},
            ),
        ),
        (
            "let return(x) = x\n(return(1), return(True), return(6.521))",
            True,
            types.TypeApply.tuple_(span, (int_type, bool_type, float_type)),
        ),
    ),
)
def test_infer_types(source, do_inference, expected_type):
    untyped_ast = _prepare(source, do_inference)
    typed_ast = type_inferer.infer_types(untyped_ast)
    assert expected_type == typed_ast.type_


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
    actual = type_inferer.unify(left, right)
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
        type_inferer.unify(left, right)


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
    actual = type_.substitute(sub)
    assert expected == actual


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
    assert expected == actual


@mark.type_inference
def test_instantiate():
    scheme = types.TypeScheme(
        types.TypeApply.func(span, types.TypeVar(span, "foo"), int_type),
        {types.TypeVar(span, "foo")},
    )
    result = type_inferer.instantiate(scheme)
    assert not isinstance(result, types.TypeScheme)


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
    actual = type_inferer.generalise(type_)
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
    result = type_inferer.find_free_vars(type_)
    actual = {var.value for var in result}
    assert expected == actual

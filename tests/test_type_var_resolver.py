from pytest import mark

from context import base, typed, types, type_var_resolver

span = (0, 0)


@mark.parametrize(
    "source,expected",
    (
        (
            types.TypeName.unit(span),
            types.TypeName.unit(span),
        ),
        (
            types.TypeName(span, "x"),
            types.TypeVar(span, "x"),
        ),
        (
            base.Define(
                span,
                typed.Name(span, types.TypeName(span, "Int"), "meaning_of_life"),
                base.Scalar(span, 42),
            ),
            base.Define(
                span,
                typed.Name(span, types.TypeName(span, "Int"), "meaning_of_life"),
                base.Scalar(span, 42),
            ),
        ),
        (
            base.Define(
                span,
                typed.Name(span, types.TypeName(span, "a"), "pi"),
                base.Scalar(span, 3.1412),
            ),
            base.Define(
                span,
                typed.Name(span, types.TypeVar(span, "a"), "pi"),
                base.Scalar(span, 3.1412),
            ),
        ),
    ),
)
def test_resolve_type_vars(source, expected):
    actual = type_var_resolver.resolve_type_vars(source)
    assert expected == actual

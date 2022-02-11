# pylint: disable=C0116
from os.path import sep
from pytest import mark

from context import base, string_expander

span = (0, 0)


@mark.parametrize(
    "source,expected",
    (
        ("\\f", "\f"),
        ("\\5F", "_"),
        ("\\u005F", "_"),
        ("\\U00005f", "_"),
        ("\\u039B", "Λ"),
        ("\\U0003c2", "ς"),
        ("\\U01F4A9", "💩"),
    ),
)
def test_expand_string(source, expected):
    actual = string_expander.expand_string(source)
    assert expected == actual


@mark.parametrize(
    "tree,expected",
    (
        (
            base.Scalar(span, "\\U01F4A9"),
            base.Scalar(span, "💩"),
        ),
        (
            base.Cond(
                span,
                base.Scalar(span, False),
                base.Scalar(span, "This is definitely not a path!"),
                base.FuncCall(
                    span,
                    base.FuncCall(span, base.Name(span, "+"), base.Scalar(span, "C:")),
                    base.Scalar(span, "\\/Users"),
                ),
            ),
            base.Cond(
                span,
                base.Scalar(span, False),
                base.Scalar(span, "This is definitely not a path!"),
                base.FuncCall(
                    span,
                    base.FuncCall(span, base.Name(span, "+"), base.Scalar(span, "C:")),
                    base.Scalar(span, f"{sep}Users"),
                ),
            ),
        ),
    ),
)
def test_expand_strings(tree, expected):
    actual = string_expander.expand_strings(tree)
    assert expected == actual

# pylint: disable=C0116, W0212
from pytest import mark

from context import base, lex, parse

span = (0, 0)

_prepare = lambda source: lex.infer_eols(lex.lex(source))


@mark.integration
@mark.parsing
@mark.parametrize(
    "source,expected",
    (
        ("", base.Unit(span)),
        ("False", base.Scalar(span, False)),
        ("(True)", base.Scalar(span, True)),
        ("845.3142", base.Scalar(span, 845.3142)),
        ('"αβγ"', base.Scalar(span, "αβγ")),
        ("()", base.Unit(span)),
        (
            "[1, 2, 3, 4, 5]",
            base.List(
                span,
                (
                    base.Scalar(span, 1),
                    base.Scalar(span, 2),
                    base.Scalar(span, 3),
                    base.Scalar(span, 4),
                    base.Scalar(span, 5),
                ),
            ),
        ),
        (
            'print_line("Hello " + "World")',
            base.Apply(
                span,
                base.Name(span, "print_line"),
                base.Apply(
                    span,
                    base.Apply(span, base.Name(span, "+"), base.Scalar(span, "Hello ")),
                    base.Scalar(span, "World"),
                ),
            ),
        ),
        (
            "21 ^ -2",
            base.Apply(
                span,
                base.Apply(span, base.Name(span, "^"), base.Scalar(span, 21)),
                base.Apply(span, base.Name(span, "~"), base.Scalar(span, 2)),
            ),
        ),
        (
            "let xor(a, b) = (a or b) and not (a and b)",
            base.Define(
                span,
                base.Name(span, "xor"),
                base.Function.curry(
                    span,
                    [base.Name(span, "a"), base.Name(span, "b")],
                    base.Apply(
                        span,
                        base.Apply(
                            span,
                            base.Name(span, "and"),
                            base.Apply(
                                span,
                                base.Apply(
                                    span, base.Name(span, "or"), base.Name(span, "a")
                                ),
                                base.Name(span, "b"),
                            ),
                        ),
                        base.Apply(
                            span,
                            base.Name(span, "not"),
                            base.Apply(
                                span,
                                base.Apply(
                                    span,
                                    base.Name(span, "and"),
                                    base.Name(span, "a"),
                                ),
                                base.Name(span, "b"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            "\\x, y, z -> x - y - (z + 1)",
            base.Function.curry(
                span,
                [base.Name(span, "x"), base.Name(span, "y"), base.Name(span, "z")],
                base.Apply(
                    span,
                    base.Apply(
                        span,
                        base.Name(span, "-"),
                        base.Apply(
                            span,
                            base.Apply(
                                span, base.Name(span, "-"), base.Name(span, "x")
                            ),
                            base.Name(span, "y"),
                        ),
                    ),
                    base.Apply(
                        span,
                        base.Apply(span, base.Name(span, "+"), base.Name(span, "z")),
                        base.Scalar(span, 1),
                    ),
                ),
            ),
        ),
        (
            '(141, return(True), pi, "", ())',
            base.Pair(
                span,
                base.Scalar(span, 141),
                base.Pair(
                    span,
                    base.Apply(
                        span, base.Name(span, "return"), base.Scalar(span, True)
                    ),
                    base.Pair(
                        span,
                        base.Name(span, "pi"),
                        base.Pair(
                            span,
                            base.Scalar(span, ""),
                            base.Unit(span),
                        ),
                    ),
                ),
            ),
        ),
        (
            "let pair = (func_1(1, 2), func_2(3, 4))",
            base.Define(
                span,
                base.Name(span, "pair"),
                base.Pair(
                    span,
                    base.Apply(
                        span,
                        base.Apply(
                            span, base.Name(span, "func_1"), base.Scalar(span, 1)
                        ),
                        base.Scalar(span, 2),
                    ),
                    base.Apply(
                        span,
                        base.Apply(
                            span, base.Name(span, "func_2"), base.Scalar(span, 3)
                        ),
                        base.Scalar(span, 4),
                    ),
                ),
            ),
        ),
    ),
)
def test_parser(source, expected):
    lexed_source = _prepare(source)
    actual = parse.parse(lexed_source)
    assert expected == actual

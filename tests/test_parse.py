# pylint: disable=C0116, W0212
from pytest import mark

from context import base, lex, parse

span = (0, 0)


def _prepare(source: str, inference_on: bool = True) -> lex.TokenStream:
    """
    Prepare a `TokenStream` for the lexer to use from a source string.
    """
    inferer = lex.infer_eols if inference_on else (lambda string: string)
    return lex.TokenStream(inferer(lex.lex(source)))


@mark.integration
@mark.parsing
@mark.parametrize(
    "source,expected",
    (
        ("", base.Vector.unit(span)),
        ("False", base.Scalar(span, False)),
        ("(True)", base.Scalar(span, True)),
        ("845.3142", base.Scalar(span, 845.3142)),
        ('"αβγ"', base.Scalar(span, "αβγ")),
        ("()", base.Vector.unit(span)),
        ("3.142", base.Scalar(span, 3.142)),
        ("(3.142,)", base.Scalar(span, 3.142)),
        (
            "[1, 2, 3, 4, 5]",
            base.Vector(
                span,
                base.VectorTypes.LIST,
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
            base.FuncCall(
                span,
                base.Name(span, "print_line"),
                base.FuncCall(
                    span,
                    base.FuncCall(
                        span, base.Name(span, "+"), base.Scalar(span, "Hello ")
                    ),
                    base.Scalar(span, "World"),
                ),
            ),
        ),
        (
            "21 ^ -2",
            base.FuncCall(
                span,
                base.FuncCall(span, base.Name(span, "^"), base.Scalar(span, 21)),
                base.FuncCall(span, base.Name(span, "~"), base.Scalar(span, 2)),
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
                    base.FuncCall(
                        span,
                        base.FuncCall(
                            span,
                            base.Name(span, "and"),
                            base.FuncCall(
                                span,
                                base.FuncCall(
                                    span, base.Name(span, "or"), base.Name(span, "a")
                                ),
                                base.Name(span, "b"),
                            ),
                        ),
                        base.FuncCall(
                            span,
                            base.Name(span, "not"),
                            base.FuncCall(
                                span,
                                base.FuncCall(
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
                base.FuncCall(
                    span,
                    base.FuncCall(
                        span,
                        base.Name(span, "-"),
                        base.FuncCall(
                            span,
                            base.FuncCall(span, base.Name(span, "-"), base.Name(span, "x")),
                            base.Name(span, "y"),
                        ),
                    ),
                    base.FuncCall(
                        span,
                        base.FuncCall(span, base.Name(span, "+"), base.Name(span, "z")),
                        base.Scalar(span, 1),
                    ),
                ),
            ),
        ),
    ),
)
def test_parser(source, expected):
    lexed_source = _prepare(source, False)
    actual = parse.parse(lexed_source)
    assert expected == actual

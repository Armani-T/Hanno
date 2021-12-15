# pylint: disable=C0116, W0212
from pytest import mark

from context import base, lex, parse


def _prepare(source: str, inference_on: bool = True) -> lex.TokenStream:
    """
    Prepare a `TokenStream` for the lexer to use from a source string.
    """
    inferer = lex.infer_eols if inference_on else (lambda string: string)
    return lex.TokenStream(inferer(lex.lex(source)))


@mark.integration
@mark.parsing
def test_parser_on_empty_token_stream():
    stream = lex.TokenStream(iter(()))
    result = parse.parse(stream)
    assert isinstance(result, base.Vector)
    assert result.vec_type == base.VectorTypes.TUPLE
    assert not result.elements


@mark.integration
@mark.parsing
@mark.parametrize(
    "source,expected",
    (
        ("False", base.Scalar((0, 5), False)),
        ("(True)", base.Scalar((0, 4), True)),
        ("845.3142", base.Scalar((0, 7), 845.3142)),
        ("124", base.Scalar((0, 3), 124)),
        ('"αβγ"', base.Scalar((0, 3), "αβγ")),
        ("()", base.Vector.unit((0, 2))),
        ("3.142", base.Scalar((1, 6), 3.142)),
        ("(3.142,)", base.Scalar((1, 6), 3.142)),
        (
            "[1, 2, 3, 4, 5]",
            base.Vector(
                (0, 15),
                base.VectorTypes.LIST,
                (
                    base.Scalar((0, 0), 1),
                    base.Scalar((0, 0), 2),
                    base.Scalar((0, 0), 3),
                    base.Scalar((0, 0), 4),
                    base.Scalar((0, 0), 5),
                ),
            ),
        ),
    ),
)
def test_parser(source, expected):
    lexed_source = _prepare(source, False)
    actual = parse.parse(lexed_source)
    assert expected == actual

from pytest import mark

from context import base, lex, parse


def prepare(source: str, inference_on: bool = True) -> lex.TokenStream:
    """
    Prepare a `TokenStream` for the lexer to use from a source string.
    """
    inferer = lex.infer_eols if inference_on else (lambda string: string)
    return lex.TokenStream(inferer(lex.lex(source)))


@mark.parsing
def test_program_rule_when_token_stream_is_empty():
    stream = lex.TokenStream(iter(()))
    result = parse._program(stream)
    assert isinstance(result, base.Vector)
    assert result.vec_type == base.VectorTypes.TUPLE
    assert not result.elements


@mark.parsing
@mark.parametrize(
    "source,size,ends",
    (
        ("e, 3 * (10 ^ 8), epsilon, 344)", 4, (lex.TokenTypes.rparen,)),
        ('"a", "b", "c", "d", "e",]', 5, (lex.TokenTypes.rbracket,)),
        ('"a", "b", "c", "d", "e",)', 5, (lex.TokenTypes.rparen,)),
    ),
)
def test_elements_rule(source, size, ends):
    result = parse._elements(prepare(source, False), *ends)
    assert len(result) == size
    assert all((isinstance(elem, base.ASTNode) for elem in result))


@mark.parsing
@mark.parametrize(
    "source,expected",
    (
        ("()", base.Vector((0, 2), base.VectorTypes.TUPLE, ())),
        ("(3.142)", base.Scalar((1, 6), base.ScalarTypes.FLOAT, "3.142")),
        ("(3.142,)", base.Scalar((1, 6), base.ScalarTypes.FLOAT, "3.142")),
        (
            '("α", "β", "γ")',
            base.Vector(
                (0, 15),
                base.VectorTypes.TUPLE,
                (
                    base.Scalar((1, 4), base.ScalarTypes.STRING, '"α"'),
                    base.Scalar((6, 9), base.ScalarTypes.STRING, '"β"'),
                    base.Scalar((11, 14), base.ScalarTypes.STRING, '"γ"'),
                ),
            ),
        ),
    ),
)
def test_tuple_rule(source, expected):
    actual = parse._tuple(prepare(source, False))
    assert expected == actual


@mark.parsing
@mark.parametrize(
    "source,expected_type",
    (
        ("False", base.ScalarTypes.BOOL),
        ("845.3142", base.ScalarTypes.FLOAT),
        ('"Hello, World!"', base.ScalarTypes.STRING),
    ),
)
def test_scalar_rule(source, expected_type):
    actual = parse._scalar(prepare(source, False))
    assert isinstance(actual, (base.Name, base.Scalar))
    assert actual.value_string is not None
    assert expected_type == actual.scalar_type

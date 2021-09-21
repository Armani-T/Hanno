# pylint: disable=C0116, W0212
from pytest import mark, raises

from context import base, errors, lex, parse


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
        ("(3.142)", base.Scalar((1, 6), 3.142)),
        ("(3.142,)", base.Scalar((1, 6), 3.142)),
        (
            '("α", "β", "γ")',
            base.Vector(
                (0, 15),
                base.VectorTypes.TUPLE,
                (
                    base.Scalar((1, 4), "α"),
                    base.Scalar((6, 9), "β"),
                    base.Scalar((11, 14), "γ"),
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
    "source,expected",
    (
        ("False", False),
        ("True", True),
        ("845.3142", 845.3142),
        ("124", 124),
        ('"Hello, World!"', "Hello, World!"),
        ("some_var_name", "some_var_name"),
        # NOTE: This builds a `Name`, NOT a `Scalar` with a `str` value
    ),
)
def test_scalar_rule(source, expected):
    actual = parse._scalar(prepare(source, False))
    assert isinstance(actual, (base.Name, base.Scalar))
    assert expected == actual.value


@mark.parsing
@mark.parametrize(
    "source,expected_length",
    (
        ("x)", 1),
        ("x,)", 1),
        ("base, exp)", 2),
        ("string, encoding, on_success, on_failure, ->", 4),
    ),
)
def test_params_rule(source, expected_length):
    actual = parse._params(prepare(source, False))
    assert all(map(lambda arg: isinstance(arg, base.Name), actual))
    assert expected_length > 0
    assert expected_length == len(actual)


@mark.parsing
def test_params_fails_on_0_parameters():
    with raises(errors.UnexpectedTokenError):
        stream = lex.TokenStream(iter([lex.Token((0, 1), lex.TokenTypes.comma, None)]))
        parse._params(stream)

from pytest import mark

from context import ast
from context import lex
from context import parse


def prepare(source: str, inference_on: bool = True) -> lex.TokenStream:
    """
    Prepare a `TokenStream` for the lexer to use from a source string.
    """
    inferer = lex.infer_eols if inference_on else (lambda stream: stream)
    return lex.TokenStream(inferer(lex.lex(source)))


@mark.parser
def test_program_rule_when_token_stream_is_empty():
    stream = lex.TokenStream(iter(()))
    result = parse._program(stream)
    assert isinstance(result, ast.Vector)
    assert result.vec_type == ast.VectorTypes.TUPLE
    assert not result.elements


@mark.parser
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
    assert all((isinstance(elem, ast.ASTNode) for elem in result))


@mark.parser
@mark.parametrize(
    "source,expected",
    (
        ("()", ast.Vector((0, 2), ast.VectorTypes.TUPLE, ())),
        ("(3.142)", ast.Scalar((1, 6), ast.ScalarTypes.FLOAT, "3.142")),
        ("(3.142,)", ast.Scalar((1, 6), ast.ScalarTypes.FLOAT, "3.142")),
        (
            '("α", "β", "γ")',
            ast.Vector(
                (0, 15),
                ast.VectorTypes.TUPLE,
                (
                    ast.Scalar((1, 4), ast.ScalarTypes.STRING, '"α"'),
                    ast.Scalar((6, 9), ast.ScalarTypes.STRING, '"β"'),
                    ast.Scalar((11, 14), ast.ScalarTypes.STRING, '"γ"'),
                ),
            ),
        ),
    ),
)
def test_tuple_rule(source, expected):
    result = parse._tuple(prepare(source, False))
    assert result == expected


@mark.parser
@mark.parametrize(
    "source,expected_type",
    (
        ("False", ast.ScalarTypes.BOOL),
        ("845.3142", ast.ScalarTypes.FLOAT),
        ('"Hello, World!"', ast.ScalarTypes.STRING),
    ),
)
def test_scalar_rule(source, expected_type):
    result = parse._scalar(prepare(source, False))
    assert isinstance(result, (ast.Name, ast.Scalar))
    assert result.scalar_type == expected_type
    assert result.value_string is not None

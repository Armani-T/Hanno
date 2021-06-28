# pylint: disable=C0116, W0612
from pytest import main, mark, raises

from hasdrubal import lex
from hasdrubal.errors import BadEncodingError

TT = lex.TokenTypes


@mark.lexer
@mark.parametrize(
    "source,expected",
    (
        (b"", ""),
        (b"English", "English"),
        (b"Fran\xc3\xa7ais", "Français"),
        (b"ma\xc3\xb1ana ol\xc3\xa9", "mañana olé"),
        (b"\xcf\x89\xcf\x81\xce\xaf", "ωρί"),
        (b"\xd0\x94\xd0\xb5\xd1\x81\xd1\x8f\xd1\x82", "Десят"),
        (b"\xe3\x83\xa6\xe3\x82\xb6\xe3\x83\xbc\xe5\x88\xa5\xe3\x82\xb5", "ユザー別サ"),
    ),
)
def test_to_utf8(source, expected):
    assert lex.to_utf8(source) == expected


@mark.lexer
@mark.parametrize(
    "source",
    (
        b"\xcf\x89\xcf\x81\xcf",
        b"\xe3\x83\xa6\xe3\x82\xb6\xe3\x83\xbc\xe5\x88\xa5\xe3\x82",
    ),
)
def test_to_utf8_raises_bad_encoding_error(source):
    with raises(BadEncodingError):
        lex.to_utf8(source)


@mark.lexer
@mark.parametrize(
    "source,expected_tokens",
    (
        ("", ()),
        ("var", (lex.Token((0, 3), TT.name, "var"),)),
        ("100", (lex.Token((3, 6), TT.integer, "100"),)),
        (
            "let pi = 3.14",
            (
                lex.Token(0, TT.let, None),
                lex.Token(0, TT.name, "pi"),
                lex.Token(0, TT.equal, None),
                lex.Token(0, TT.float_, "3.14"),
            ),
        ),
    ),
)
def test_gen_tokens(source, expected_tokens):
    actual_tokens = lex.gen_tokens(source)
    assert tuple(actual_tokens) == tuple(expected_tokens)

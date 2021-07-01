# pylint: disable=C0116, W0612
from pytest import mark, raises

from context import lex
from context import errors


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
    with raises(errors.BadEncodingError):
        lex.to_utf8(source)


@mark.lexer
@mark.parametrize(
    "source,expected_tokens",
    (
        ("", ()),
        ("100", (lex.Token((0, 3), lex.TokenTypes.integer, "100"),)),
        (
            "let pi = 3.14",
            (
                lex.Token((0, 3), lex.TokenTypes.let, None),
                lex.Token((4, 6), lex.TokenTypes.name, "pi"),
                lex.Token((7, 8), lex.TokenTypes.equal, None),
                lex.Token((9, 13), lex.TokenTypes.float_, "3.14"),
            ),
        ),
    ),
)
def test_lex(source, expected_tokens):
    actual_tokens = tuple(lex.lex(source))
    assert actual_tokens == tuple(expected_tokens)


@mark.semicolon_inference
@mark.parametrize(
    "stream,expected",
    (
        ((), ()),
        (
            (lex.Token((0, 3), lex.TokenTypes.float_, "1.01"),),
            (
                lex.Token((0, 1), lex.TokenTypes.float_, "1.01"),
                lex.Token((1, 2), lex.TokenTypes.eol, None),
            ),
        ),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.integer, "1"),
                lex.Token((1, 2), lex.TokenTypes.diamond, None),
                lex.Token((2, 3), lex.TokenTypes.integer, "1"),
            ),
            (
                lex.Token((0, 1), lex.TokenTypes.integer, "1"),
                lex.Token((1, 2), lex.TokenTypes.diamond, None),
                lex.Token((2, 3), lex.TokenTypes.integer, "1"),
                lex.Token((2, 3), lex.TokenTypes.eol, None),
            ),
        ),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((1, 2), lex.TokenTypes.rbracket, None),
            ),
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((1, 2), lex.TokenTypes.rbracket, None),
                lex.Token((2, 3), lex.TokenTypes.eol, None),
            ),
        ),
    )
)
def test_infer_eols(stream, expected):
    actual = tuple(lex.infer_eols(stream))
    expected = tuple(expected)
    assert actual == expected

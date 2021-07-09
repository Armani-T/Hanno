# pylint: disable=C0116, W0612
from pytest import mark, raises

from context import lex
from context import errors
from utils import FakeMatch


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


@mark.lexer
@mark.parametrize(
    "match,accepted_newlines",
    (
        (
            FakeMatch((0, 1), "cr_newline", "\r"),
            ("lf_newline", "crlf_newline"),
        ),
        (
            FakeMatch((0, 1), "crlf_newline", "\r\n"),
            ("lf_newline",),
        ),
        (
            FakeMatch((0, 1), "cr_newline", "\r"),
            ("crlf_newline",),
        ),
    ),
)
def test_build_token_fails_on_invalid_newline(match, accepted_newlines):
    with raises(errors.IllegalCharError):
        lex.build_token(match, "", accepted_newlines)


@mark.semicolon_inference
@mark.parametrize(
    "stream,expected",
    (
        ((), ()),
        (
            (lex.Token((0, 3), lex.TokenTypes.float_, "1.01"),),
            (
                lex.Token((0, 3), lex.TokenTypes.float_, "1.01"),
                lex.Token((3, 4), lex.TokenTypes.eol, None),
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
                lex.Token((3, 4), lex.TokenTypes.eol, None),
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
    ),
)
def test_infer_eols(stream, expected):
    actual = tuple(lex.infer_eols(stream))
    expected = tuple(expected)
    assert actual == expected


@mark.semicolon_inference
@mark.parametrize(
    "prev,next_",
    (
        (
            lex.Token((0, 1), lex.TokenTypes.integer, "100"),
            lex.Token((2, 3), lex.TokenTypes.integer, "100"),
        ),
        (
            lex.Token((86, 87), lex.TokenTypes.rparen, None),
            lex.Token((88, 89), lex.TokenTypes.let, None),
        ),
    ),
)
def test_can_add_eol_returns_true(prev, next_):
    assert lex.can_add_eol(prev, next_, 0)


@mark.semicolon_inference
@mark.parametrize(
    "prev,next_,stack_size",
    (
        (
            lex.Token((0, 1), lex.TokenTypes.diamond, None),
            lex.Token((2, 3), lex.TokenTypes.integer, "100"),
            0,
        ),
        (
            lex.Token((0, 1), lex.TokenTypes.diamond, None),
            lex.Token((2, 3), lex.TokenTypes.integer, "100"),
            3,
        ),
    ),
)
def test_can_add_eol_returns_false(prev, next_, stack_size):
    assert not lex.can_add_eol(prev, next_, stack_size)


@mark.lexer
@mark.parametrize(
    "tokens",
    (
        (),
        (lex.Token((0, 1), lex.TokenTypes.dash, None),),
        (
            lex.Token((0, 1), lex.TokenTypes.dash, None),
            lex.Token((0, 1), lex.TokenTypes.float_, "2.7182"),
        ),
    ),
)
def test_show_tokens(tokens):
    result = lex.show_tokens(tokens)
    assert isinstance(result, str)
    assert result.count("\n") == max(0, len(tokens) - 1)


@mark.lexer
@mark.parametrize(
    "tokens",
    (
        (lex.Token((2, 3), lex.TokenTypes.eol, None),),
        (
            lex.Token((0, 1), lex.TokenTypes.lbracket, None),
            lex.Token((2, 5), lex.TokenTypes.integer, "100"),
            lex.Token((6, 7), lex.TokenTypes.dash, None),
            lex.Token((8, 9), lex.TokenTypes.integer, "0"),
            lex.Token((10, 11), lex.TokenTypes.rbracket, None),
        ),
    ),
)
def test_tokenstream_advance(tokens):
    inst = lex.TokenStream((token for token in tokens))
    for expected in tokens:
        actual = inst._advance()
        assert actual == expected


def test_empty_tokenstream_advance_raises_unexpected_eof_error():
    inst = lex.TokenStream((token for token in ()))
    with raises(errors.UnexpectedEOFError):
        inst._advance()


@mark.lexer
@mark.parametrize(
    "tokens,expected",
    (
        ((), False),
        ((lex.Token((2, 3), lex.TokenTypes.eol, None),), True),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((2, 5), lex.TokenTypes.integer, "100"),
                lex.Token((6, 7), lex.TokenTypes.dash, None),
                lex.Token((8, 9), lex.TokenTypes.integer, "0"),
                lex.Token((10, 11), lex.TokenTypes.rbracket, None),
            ),
            True,
        ),
    ),
)
def test_tokenstream_eval_to_bool(tokens, expected):
    inst = lex.TokenStream((token for token in tokens))
    if expected:
        assert inst
    else:
        assert not inst


@mark.lexer
@mark.parametrize(
    "tokens,cache",
    (
        (
            (),
            (lex.Token((2, 5), lex.TokenTypes.float_, "3.142"),),
        ),
        (
            (
                lex.Token((6, 7), lex.TokenTypes.dash, None),
                lex.Token((8, 9), lex.TokenTypes.integer, "0"),
                lex.Token((10, 11), lex.TokenTypes.rbracket, None),
            ),
            (
                lex.Token((2, 5), lex.TokenTypes.integer, "100"),
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
            ),
        ),
    ),
)
def test_tokenstream_eval_to_bool_with_nonempty_cache(tokens, cache):
    inst = lex.TokenStream((token for token in tokens))
    inst._cache = cache
    assert inst


@mark.lexer
@mark.parametrize(
    "tokens,expected",
    (
        (
            (lex.Token((2, 3), lex.TokenTypes.eol, None),),
            (lex.TokenTypes.eol,),
        ),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((2, 5), lex.TokenTypes.integer, "100"),
                lex.Token((6, 7), lex.TokenTypes.dash, None),
                lex.Token((8, 9), lex.TokenTypes.integer, "0"),
                lex.Token((10, 11), lex.TokenTypes.rbracket, None),
            ),
            (lex.TokenTypes.lparen, lex.TokenTypes.lbracket),
        ),
    ),
)
def test_tokenstream_consume_success(tokens, expected):
    inst = lex.TokenStream((token for token in tokens))
    result = inst.consume(*expected)
    assert result.type_ in expected
    if inst:
        assert result != inst._advance()


@mark.lexer
@mark.parametrize(
    "tokens,expected,expected_errors",
    (
        ((), (), (errors.UnexpectedEOFError,)),
        (
            (lex.Token((0, 1), lex.TokenTypes.eol, None),),
            (lex.TokenTypes.integer, lex.TokenTypes.float_),
            (errors.UnexpectedTokenError,),
        ),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((2, 5), lex.TokenTypes.integer, "100"),
                lex.Token((6, 7), lex.TokenTypes.dash, None),
                lex.Token((8, 9), lex.TokenTypes.integer, "0"),
                lex.Token((10, 11), lex.TokenTypes.rbracket, None),
            ),
            (lex.TokenTypes.float_, lex.TokenTypes.integer, lex.TokenTypes.string),
            (errors.UnexpectedTokenError,),
        ),
    ),
)
def test_tokenstream_consume_fail(tokens, expected, expected_errors):
    inst = lex.TokenStream((token for token in tokens))
    with raises(*expected_errors):
        inst.consume(*expected)


@mark.lexer
@mark.parametrize(
    "tokens,expected_types,expected",
    (
        (
            (lex.Token((2, 3), lex.TokenTypes.eol, None),),
            (lex.TokenTypes.eol,),
            True,
        ),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((2, 5), lex.TokenTypes.integer, "100"),
                lex.Token((6, 7), lex.TokenTypes.dash, None),
                lex.Token((8, 9), lex.TokenTypes.integer, "0"),
                lex.Token((10, 11), lex.TokenTypes.rbracket, None),
            ),
            (lex.TokenTypes.lparen, lex.TokenTypes.lbracket),
            True,
        ),
    ),
)
def test_tokenstream_consume_if(tokens, expected_types, expected):
    inst = lex.TokenStream((token for token in tokens))
    if expected:
        assert inst.consume_if(*expected_types)
    else:
        assert not inst.consume_if(*expected_types)


@mark.lexer
@mark.parametrize(
    "tokens,expected_types,expected",
    (
        ((), (), False),
        (
            (lex.Token((2, 3), lex.TokenTypes.eol, None),),
            (lex.TokenTypes.eol,),
            True,
        ),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((2, 5), lex.TokenTypes.integer, "100"),
                lex.Token((6, 7), lex.TokenTypes.dash, None),
                lex.Token((8, 9), lex.TokenTypes.integer, "0"),
                lex.Token((10, 11), lex.TokenTypes.rbracket, None),
            ),
            (lex.TokenTypes.lparen, lex.TokenTypes.lbracket),
            True,
        ),
    ),
)
def test_tokenstream_peek(tokens, expected_types, expected):
    inst = lex.TokenStream((token for token in tokens))
    assert inst.peek(*expected_types) is expected


@mark.lexer
def test_tokenstream_peek_with_nonempty_cache():
    tokens = (
        lex.Token((6, 7), lex.TokenTypes.dash, None),
        lex.Token((8, 9), lex.TokenTypes.integer, "0"),
        lex.Token((10, 11), lex.TokenTypes.rbracket, None),
    )
    inst = lex.TokenStream((token for token in tokens))
    inst._cache = [
        lex.Token((2, 5), lex.TokenTypes.integer, "100"),
        lex.Token((0, 1), lex.TokenTypes.lbracket, None),
    ]
    assert inst.peek(lex.TokenTypes.lbracket, lex.TokenTypes.lparen)

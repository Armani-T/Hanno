# pylint: disable=C0116, W0612, W0212
from pytest import mark, raises

from context import errors, lex


@mark.lexing
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
    assert expected == lex.to_utf8(source)


@mark.lexing
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


@mark.lexing
@mark.parametrize(
    "source,expected_tokens",
    (
        ("", ()),
        ("100", (lex.Token((0, 3), lex.TokenTypes.integer, "100"),)),
        (
            "let pi = 3.14",
            (
                lex.Token((0, 3), lex.TokenTypes.let, None),
                lex.Token((3, 4), lex.TokenTypes.whitespace, " "),
                lex.Token((4, 6), lex.TokenTypes.name_, "pi"),
                lex.Token((6, 7), lex.TokenTypes.whitespace, " "),
                lex.Token((7, 8), lex.TokenTypes.equal, None),
                lex.Token((8, 9), lex.TokenTypes.whitespace, " "),
                lex.Token((9, 13), lex.TokenTypes.float_, "3.14"),
            ),
        ),
        (
            "let avg :=\n#An average over `values`.\nlet sum = -fold(add, values, 0)",
            (
                lex.Token((0, 3), lex.TokenTypes.let, None),
                lex.Token((3, 4), lex.TokenTypes.whitespace, " "),
                lex.Token((4, 7), lex.TokenTypes.name_, "avg"),
                lex.Token((7, 8), lex.TokenTypes.whitespace, " "),
                lex.Token((8, 10), lex.TokenTypes.colon_equal, None),
                lex.Token((10, 11), lex.TokenTypes.whitespace, "\n"),
                lex.Token((11, 37), lex.TokenTypes.comment, "#An average over `values`."),
                lex.Token((38, 41), lex.TokenTypes.let, None),
                lex.Token((41, 42), lex.TokenTypes.whitespace, " "),
                lex.Token((42, 45), lex.TokenTypes.name_, "sum"),
                lex.Token((45, 46), lex.TokenTypes.whitespace, " "),
                lex.Token((46, 47), lex.TokenTypes.equal, None),
                lex.Token((47, 48), lex.TokenTypes.whitespace, " "),
                lex.Token((48, 49), lex.TokenTypes.dash, None),
                lex.Token((49, 53), lex.TokenTypes.name_, "fold"),
                lex.Token((53, 54), lex.TokenTypes.lparen, None),
                lex.Token((54, 57), lex.TokenTypes.name_, "add"),
                lex.Token((57, 58), lex.TokenTypes.comma, None),
                lex.Token((58, 59), lex.TokenTypes.whitespace, " "),
                lex.Token((59, 65), lex.TokenTypes.name_, "values"),
                lex.Token((65, 66), lex.TokenTypes.comma, None),
                lex.Token((66, 67), lex.TokenTypes.whitespace, " "),
                lex.Token((67, 68), lex.TokenTypes.integer, "0"),
                lex.Token((68, 69), lex.TokenTypes.rparen, None),
            ),
        ),
    ),
)
def test_lex(source, expected_tokens):
    actual_tokens = tuple(lex.lex(source))
    expected = tuple(expected_tokens)
    assert expected == actual_tokens


@mark.lexing
@mark.parametrize(
    "source,accepted_newlines",
    (
        (
            "Hello\r\nWorld",
            ("\n", "\r"),
        ),
        (
            "identity(\r\n1\r\n)",
            ("\n",),
        ),
        (
            "is_running and\riterations > 100",
            ("\r\n",),
        ),
    ),
)
def test_normalise_newlines_for_failures(source, accepted_newlines):
    with raises(errors.IllegalCharError):
        lex.normalise_newlines(source, accepted_newlines)


@mark.lexing
@mark.parametrize(
    "source,expected,accepted_newlines",
    (
        (
            'lorem = "ipsum"\rid(\rasciping\r)\r',
            'lorem = "ipsum"\nid(\nasciping\n)\n',
            ("\r", "\n"),
        ),
        (
            "(3 * j) + \r\n1\r\n",
            "(3 * j) + \n1\n",
            ("\r\n",),
        ),
        (
            "is_running and\riterations > 100",
            "is_running and\niterations > 100",
            ("\r", "\n", "\r\n"),
        ),
    ),
)
def test_normalise_newlines(source, expected, accepted_newlines):
    actual = lex.normalise_newlines(source, accepted_newlines)
    assert expected == actual


@mark.eol_inference
@mark.parametrize(
    "tokens,expected_tokens",
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
def test_infer_eols(tokens, expected_tokens):
    expected = lex.TokenStream(iter(expected_tokens), ())
    stream = lex.TokenStream(iter(tokens), ())
    actual = lex.infer_eols(stream)
    assert expected == actual


@mark.eol_inference
@mark.parametrize(
    "prev,current,next_",
    (
        (
            lex.Token((0, 3), lex.TokenTypes.integer, "100"),
            lex.Token((3, 4), lex.TokenTypes.whitespace, "\n"),
            lex.Token((4, 7), lex.TokenTypes.integer, "100"),
        ),
        (
            lex.Token((86, 87), lex.TokenTypes.rparen, None),
            lex.Token((87, 90), lex.TokenTypes.whitespace, "\n  "),
            lex.Token((90, 93), lex.TokenTypes.let, None),
        ),
    ),
)
def test_can_add_eol_returns_true(prev, current, next_):
    assert lex.can_add_eol(prev, current, next_, 0)


@mark.eol_inference
@mark.parametrize(
    "prev,current,next_,stack_size",
    (
        (
            lex.Token((0, 1), lex.TokenTypes.diamond, None),
            lex.Token((0, 1), lex.TokenTypes.whitespace, "  "),
            lex.Token((2, 3), lex.TokenTypes.integer, "100"),
            0,
        ),
        (
            lex.Token((0, 1), lex.TokenTypes.diamond, None),
            lex.Token((0, 1), lex.TokenTypes.whitespace, "\n\t\t\t"),
            lex.Token((2, 3), lex.TokenTypes.integer, "100"),
            3,
        ),
    ),
)
def test_can_add_eol_returns_false(prev, current, next_, stack_size):
    assert not lex.can_add_eol(prev, current, next_, stack_size)


@mark.lexing
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
    stream = lex.TokenStream(iter(tokens), ())
    result = stream.show()
    max_newlines = max(0, len(tokens) - 1)
    assert isinstance(result, str)
    assert result.count("\n") == max_newlines


@mark.lexing
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
def test_token_stream_advance(tokens):
    inst = lex.TokenStream(iter(tokens), ())
    for expected in tokens:
        actual = inst._advance()
        assert expected == actual


def test_empty_token_stream_advance_raises_unexpected_eof_error():
    inst = lex.TokenStream((token for token in ()), ())
    inst._advance()  # To (hopefully) take care of the EOF token.
    with raises(errors.UnexpectedEOFError):
        inst._advance()


@mark.lexing
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
def test_token_stream_eval_to_bool(tokens, expected):
    inst = lex.TokenStream(iter(tokens), ())
    inst._advance()
    if expected:
        assert inst
    else:
        assert not inst


@mark.lexing
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
def test_token_stream_eval_to_bool_with_nonempty_cache(tokens, cache):
    inst = lex.TokenStream(iter(tokens), ())
    inst._cache = cache
    assert inst


@mark.lexing
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
def test_token_stream_consume_success(tokens, expected):
    inst = lex.TokenStream(iter(tokens), ())
    result = inst.consume(*expected)
    assert result.type_ in expected
    if inst:
        assert result != inst._advance()


@mark.lexing
def test_empty_token_stream_consume_fails():
    inst = lex.TokenStream(iter(()))
    inst._advance()
    with raises(errors.UnexpectedEOFError):
        inst.consume(lex.TokenTypes.string, lex.TokenTypes.name_)


@mark.lexing
@mark.parametrize(
    "tokens,expected,expected_errors",
    (
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
def test_token_stream_consume_failure(tokens, expected, expected_errors):
    inst = lex.TokenStream(iter(tokens), ())
    with raises(*expected_errors):
        inst.consume(*expected)


@mark.lexing
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
def test_token_stream_consume_if(tokens, expected_types, expected):
    inst = lex.TokenStream(iter(tokens), ())
    if expected:
        assert inst.consume_if(*expected_types)
    else:
        assert not inst.consume_if(*expected_types)


@mark.lexing
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
def test_token_stream_peek(tokens, expected_types, expected):
    inst = lex.TokenStream(iter(tokens), ())
    assert inst.peek(*expected_types) is expected


@mark.lexing
def test_token_stream_peek_with_nonempty_cache():
    tokens = (
        lex.Token((6, 7), lex.TokenTypes.dash, None),
        lex.Token((8, 9), lex.TokenTypes.integer, "0"),
        lex.Token((10, 11), lex.TokenTypes.rbracket, None),
    )
    inst = lex.TokenStream(iter(tokens), ())
    inst._cache = [
        lex.Token((2, 5), lex.TokenTypes.integer, "100"),
        lex.Token((0, 1), lex.TokenTypes.lbracket, None),
    ]
    assert inst.peek(lex.TokenTypes.lbracket, lex.TokenTypes.lparen)

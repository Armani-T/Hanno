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
    "source,expected",
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
        (
            "let avg :=\n#An average over `values`.\nlet sum = -fold(add, values, 0)",
            (
                lex.Token((0, 3), lex.TokenTypes.let, None),
                lex.Token((4, 7), lex.TokenTypes.name, "avg"),
                lex.Token((8, 10), lex.TokenTypes.colon_equal, None),
                lex.Token((38, 41), lex.TokenTypes.let, None),
                lex.Token((42, 45), lex.TokenTypes.name, "sum"),
                lex.Token((46, 47), lex.TokenTypes.equal, None),
                lex.Token((48, 49), lex.TokenTypes.dash, None),
                lex.Token((49, 53), lex.TokenTypes.name, "fold"),
                lex.Token((53, 54), lex.TokenTypes.lparen, None),
                lex.Token((54, 57), lex.TokenTypes.name, "add"),
                lex.Token((57, 58), lex.TokenTypes.comma, None),
                lex.Token((59, 65), lex.TokenTypes.name, "values"),
                lex.Token((65, 66), lex.TokenTypes.comma, None),
                lex.Token((67, 68), lex.TokenTypes.integer, "0"),
                lex.Token((68, 69), lex.TokenTypes.rparen, None),
            ),
        ),
    ),
)
def test_lex(source, expected):
    actual = lex.lex(source, ignore=[lex.TokenTypes.comment, lex.TokenTypes.whitespace])
    for expected_token, actual_token in zip(expected, actual):
        assert expected_token == actual_token


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
def test_tokenstream_show(tokens):
    expected = max(0, len(tokens) - 1)
    result = lex.TokenStream(tokens, []).show()
    assert isinstance(result, str)
    assert expected == result.count("\n")


@mark.lexing
@mark.parametrize(
    "tokens",
    (
        [lex.Token((0, 1), lex.TokenTypes.eol, None)],
        [
            lex.Token((0, 1), lex.TokenTypes.lbracket, None),
            lex.Token((2, 5), lex.TokenTypes.integer, "100"),
            lex.Token((6, 7), lex.TokenTypes.dash, None),
            lex.Token((8, 9), lex.TokenTypes.integer, "0"),
            lex.Token((10, 11), lex.TokenTypes.rbracket, None),
        ],
    ),
)
def test_token_stream_next(tokens):
    inst = lex.TokenStream(tokens, ())
    for expected in tokens:
        actual = inst.next()
        assert expected == actual


def test_empty_token_stream_next_raises_unexpected_eof_error():
    inst = lex.TokenStream((), ())
    with raises(errors.UnexpectedEOFError):
        inst.next()


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
    inst = lex.TokenStream(tokens, ())
    if expected:
        assert inst
    else:
        assert not inst


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
    inst = lex.TokenStream(tokens, ())
    result = inst.consume(*expected)
    assert result.type_ in expected
    if inst:
        assert result != inst.next()


@mark.lexing
def test_empty_token_stream_consume_fails():
    inst = lex.TokenStream((), ())
    with raises(errors.UnexpectedEOFError):
        inst.consume(lex.TokenTypes.string, lex.TokenTypes.name)


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
    inst = lex.TokenStream(tokens, ())
    with raises(*expected_errors):
        inst.consume(*expected)


@mark.lexing
@mark.parametrize(
    "tokens,expected_types,expected",
    (
        (
            [lex.Token((102, 103), lex.TokenTypes.eol, None)],
            [lex.TokenTypes.eol],
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
    inst = lex.TokenStream(tokens, ())
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
    inst = lex.TokenStream(tokens, ())
    assert inst.peek(*expected_types) is expected

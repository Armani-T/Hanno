from json import loads

from pytest import mark, raises

from context import base, errors, lex, types

SAMPLE_SOURCE = """
let l1 = [1, 2, 3]
let l2 = [4, 5, 6]
let l = l1 <> l2
let h1, t1 = head(l1), tail(l1)
let h2, t2 = head(l2), tail(l2)
"""
SAMPLE_SOURCE_PATH = __file__
span = (0, 0)


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.UndefinedNameError(base.Name(span, "var")),
        errors.UnexpectedTokenError(
            lex.Token(span, lex.TokenTypes.bslash, None),
            lex.TokenTypes.asterisk,
            lex.TokenTypes.fslash,
            lex.TokenTypes.percent,
        ),
        errors.CircularTypeError(
            types.TypeVar(span, "z"),
            types.TypeApply.func(
                span,
                types.TypeVar(span, "z"),
                types.TypeName(span, "Bool"),
            ),
        ),
    ),
)
def test_error_to_json(exception):
    json = loads(errors.to_json(exception, SAMPLE_SOURCE, SAMPLE_SOURCE_PATH))
    assert json["source_path"] == SAMPLE_SOURCE_PATH
    assert json["error_name"] == exception.name


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError("Latin-1"),
        errors.FatalInternalError(),
        errors.IllegalCharError(span, "@"),
        errors.TypeMismatchError(
            types.TypeName(span, "Int"),
            types.TypeApply(
                span,
                types.TypeName(span, "List"),
                types.TypeName(span, "Int"),
            ),
        ),
        errors.UnexpectedEOFError(),
    ),
)
def test_error_to_alert_message(exception):
    message = errors.to_alert_message(exception, SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)
    assert len(message) <= 120


@mark.error_handling
def test_error_to_long_message():
    actual = errors.to_long_message(
        errors.CMDError(errors.CMDErrorReasons.NO_PERMISSION),
        SAMPLE_SOURCE,
        SAMPLE_SOURCE_PATH,
    )
    expected = errors.beautify(
        errors.wrap_text(
            f'We were unable to open the file "{SAMPLE_SOURCE_PATH}" because we '
            "don't have the necessary permissions. Please grant the compiler "
            "file read permissions then try again."
        ),
        SAMPLE_SOURCE_PATH,
    )
    assert expected == actual


@mark.error_handling
def test_handle_other_exceptions_json():
    message = loads(
        errors.to_json(ValueError(1.412), SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    )
    assert message["source_path"] == SAMPLE_SOURCE_PATH
    assert message["error_name"] == "internal_error"
    assert message["actual_error"] == "ValueError"


@mark.error_handling
def test_handle_other_exceptions_alert_message():
    message = errors.to_alert_message(
        Exception("random error"), SAMPLE_SOURCE, SAMPLE_SOURCE_PATH
    )
    assert message.startswith("Internal Error")
    assert "Exception" in message


@mark.error_handling
def test_handle_other_exceptions_long_message():
    message = errors.to_long_message(SyntaxError(), SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert "Internal Error" in message
    assert "SyntaxError" in message


@mark.error_handling
@mark.parametrize(
    "abs_pos,expected",
    ((0, (0, 1)), (28, (8, 3)), (76, (20, 5))),
)
def test_relative_pos(abs_pos, expected):
    actual = errors.relative_pos(abs_pos, SAMPLE_SOURCE)
    assert expected == actual


@mark.error_handling
def test_relative_pos_raises():
    with raises(ValueError):
        errors.relative_pos(1200, SAMPLE_SOURCE)


@mark.error_handling
@mark.parametrize("span", ((69, 77), (10, 19), (92, 94)))
def test_make_pointer(span):
    result = errors.make_pointer(span, SAMPLE_SOURCE)
    expected_line_index = errors.relative_pos(span[0], SAMPLE_SOURCE)[1] - 1
    expected_line = SAMPLE_SOURCE.split("\n")[expected_line_index]
    assert result.startswith(f"{expected_line_index + 1} |")
    assert expected_line in result
    assert result.count("|") >= 2
    assert result.endswith("^")


@mark.error_handling
@mark.parametrize(
    "message",
    ("", "Hello, World!", "This is an extremely long sentence that should be wrapped."),
)
def test_beautify(message):
    result = errors.beautify(message, SAMPLE_SOURCE_PATH)
    assert result.startswith("\n=" if errors.LINE_WIDTH >= 24 else "\nError")
    assert "Error Encountered" in result
    assert SAMPLE_SOURCE_PATH in result
    assert message in result

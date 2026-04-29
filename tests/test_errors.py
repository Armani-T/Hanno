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


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.UndefinedNameError(base.Name((13, 16), "var")),
        errors.UnexpectedTokenError(
            lex.Token((23, 24), lex.TokenTypes.bslash, None),
            lex.TokenTypes.asterisk,
            lex.TokenTypes.fslash,
            lex.TokenTypes.percent,
        ),
        errors.CircularTypeError(
            types.TypeVar((0, 1), "z"),
            types.TypeApply.func(
                (4, 13),
                types.TypeVar((4, 5), "z"),
                types.TypeName((9, 13), "Bool"),
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
        errors.IllegalCharError((23, 24), "@"),
        errors.TypeMismatchError(
            types.TypeName((10, 13), "Int"),
            types.TypeApply(
                (20, 30),
                types.TypeName((20, 24), "List"),
                types.TypeName((26, 29), "Int"),
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
    message_string = errors.handle_other_exceptions(
        ValueError(1.412), errors.ResultTypes.JSON, SAMPLE_SOURCE_PATH
    )
    message = loads(message_string)
    assert message["source_path"] == SAMPLE_SOURCE_PATH
    assert message["error_name"] == "internal_error"
    assert message["actual_error"] == "ValueError"


@mark.error_handling
def test_handle_other_exceptions_alert_message():
    message = errors.handle_other_exceptions(
        Exception("random error"), errors.ResultTypes.ALERT_MESSAGE, SAMPLE_SOURCE_PATH
    )
    assert message.startswith("Internal Error:")
    assert "Exception" in message


@mark.error_handling
def test_handle_other_exceptions_long_message():
    message = errors.handle_other_exceptions(
        SyntaxError(), errors.ResultTypes.LONG_MESSAGE, SAMPLE_SOURCE_PATH
    )
    assert "Internal Error:" in message
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

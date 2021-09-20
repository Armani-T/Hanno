# pylint: disable=C0116, W0612
from pytest import mark

from context import base, errors, lex, types
from utils import SAMPLE_SOURCE, SAMPLE_SOURCE_PATH


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError(),
        errors.UndefinedNameError(base.Name((13, 16), "var")),
        errors.UnexpectedTokenError(
            lex.Token((23, 24), lex.TokenTypes.bslash, None),
            lex.TokenTypes.asterisk,
            lex.TokenTypes.fslash,
            lex.TokenTypes.percent,
        ),
    ),
)
def test_to_json(exception):
    message = exception.to_json(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert "error_name" in message
    assert isinstance(message["source_path"], str)
    assert isinstance(message["error_name"], str)
    assert message["source_path"] == SAMPLE_SOURCE_PATH


@mark.error_handling
@mark.parametrize(
    "exception,check_pos",
    (
        (errors.FatalInternalError(), False),
        (errors.IllegalCharError((23, 24), "@"), True),
        (errors.UnexpectedEOFError(), True),
    ),
)
def test_to_alert_message(exception, check_pos):
    message, rel_pos = exception.to_alert_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)
    if check_pos:
        assert rel_pos[0] >= 1
        assert rel_pos[1] < (len(SAMPLE_SOURCE) - 1)
        assert len(rel_pos) == 2
    else:
        assert rel_pos is None


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.TypeMismatchError(
            types.TypeApply(
                (4, 11),
                types.TypeName((4, 8), "List"),
                types.TypeVar((9, 11), "x"),
            ),
            types.TypeName((33, 39), "String"),
        ),
        errors.CMDError(errors.CMDErrorReasons.NO_PERMISSION),
    ),
)
def test_to_long_message(exception):
    message = exception.to_long_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)

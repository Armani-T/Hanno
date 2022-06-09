# pylint: disable=C0116, W0612
from pytest import mark

from context import base, errors, lex, types

SAMPLE_SOURCE = "let l = [1, 2, 3] <> [4, 5, 6]\nhead(l)\n"
SAMPLE_SOURCE_PATH = __file__


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError("utf-16"),
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
def test_hasdrubal_error_to_json(exception):
    json = exception.to_json(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert json["source_path"] == SAMPLE_SOURCE_PATH
    assert json["error_name"] == exception.name


@mark.error_handling
@mark.parametrize(
    "exception,check_pos",
    (
        (errors.FatalInternalError(), False),
        (errors.IllegalCharError((23, 24), "@"), True),
        (errors.UnexpectedEOFError(), True),
        (errors.BadEncodingError("Latin-1"), False),
        (
            errors.TypeMismatchError(
                types.TypeName((10, 13), "Int"),
                types.TypeApply(
                    (20, 30),
                    types.TypeName((20, 24), "List"),
                    types.TypeName((26, 29), "Int"),
                ),
            ),
            True,
        ),
    ),
)
def test_hasdrubal_error_to_alert_message(exception, check_pos):
    message, rel_pos = exception.to_alert_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)
    if check_pos:
        assert len(rel_pos) == 2
        assert rel_pos[1] >= 1
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
            types.TypeName((31, 37), "String"),
        ),
        errors.CMDError(errors.CMDErrorReasons.NO_PERMISSION),
    ),
)
def test_hasdrubal_error_to_long_message(exception):
    message = exception.to_long_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)

# pylint: disable=C0116, W0612
from pytest import mark

from context import errors, types
from utils import SAMPLE_SOURCE, SAMPLE_SOURCE_PATH


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.UnexpectedEOFError(),
        errors.IllegalCharError((0, 1), "a"),
        errors.CMDError(errors.CMDErrorReasons.NO_PERMISSION),
    ),
)
def test_to_json(exception):
    json = exception.to_json(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert json["source_path"] == SAMPLE_SOURCE_PATH
    assert json["error_name"] == exception.name


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError(),
        errors.IllegalCharError((0, 1), "@"),
        errors.UnexpectedEOFError(),
        errors.TypeMismatchError(
            types.TypeName((1, 4), "Int"),
            types.TypeApply(
                (64, 74),
                types.TypeName((64, 68), "List"),
                types.TypeName((70, 73), "Int"),
            ),
        ),
    ),
)
def test_to_alert_message(exception):
    message, rel_pos = exception.to_alert_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError(),
        errors.IllegalCharError((0, 1), "a"),
        errors.FatalInternalError(TypeError()),
    ),
)
def test_to_long_message(exception):
    message = exception.to_long_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)

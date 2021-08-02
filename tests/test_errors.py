# pylint: disable=C0116, W0612
from pytest import mark

from context import errors
from utils import SAMPLE_SOURCE, SAMPLE_SOURCE_PATH


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError(),
        errors.IllegalCharError(0, "a"),
        errors.UnexpectedEOFError(),
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
        (errors.BadEncodingError(), False),
        (errors.IllegalCharError(0, "@"), True),
        (errors.UnexpectedEOFError(), True),
    ),
)
def test_to_alert_message(exception, check_pos):
    message, rel_pos = exception.to_alert_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)
    if check_pos:
        assert rel_pos[0] >= 0
        assert rel_pos[1] < (len(SAMPLE_SOURCE) - 1)
    else:
        assert rel_pos is None


@mark.error_handling
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError(),
        errors.IllegalCharError(0, "a"),
        errors.UnexpectedEOFError(),
    ),
)
def test_to_long_message(exception):
    message = exception.to_long_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)
    assert all(map(lambda line: len(line) <= errors.LINE_WIDTH, message.split("\n")))

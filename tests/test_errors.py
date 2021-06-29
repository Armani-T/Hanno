# pylint: disable=C0116, W0612
from pytest import mark

from context import errors
from utils import SAMPLE_SOURCE, SAMPLE_SOURCE_PATH


@mark.error
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError(),
        errors.IllegalCharError(0, "a"),
        errors.UnexpectedEOFError(),
    ),
)
def test_to_json(exception):
    assert issubclass(type(exception), errors.HasdrubalError)
    message = exception.to_json(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert "source_path" in message
    assert "error_name" in message
    assert isinstance(message["source_path"], str)
    assert isinstance(message["error_name"], str)
    assert message["source_path"] == SAMPLE_SOURCE_PATH


@mark.error
@mark.parametrize(
    "exception,check_pos_data",
    (
        (errors.BadEncodingError(), False),
        (errors.IllegalCharError(0, "a"), True),
        (errors.UnexpectedEOFError(), True),
    ),
)
def test_to_alert_message(exception, check_pos_data):
    assert issubclass(type(exception), errors.HasdrubalError)
    message, pos = exception.to_alert_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)
    if check_pos_data:
        assert pos >= 0
        assert pos < len(SAMPLE_SOURCE)
    else:
        assert pos is None


@mark.error
@mark.parametrize(
    "exception",
    (
        errors.BadEncodingError(),
        errors.IllegalCharError(0, "a"),
        errors.UnexpectedEOFError(),
    ),
)
def test_to_long_message(exception):
    assert issubclass(type(exception), errors.HasdrubalError)
    message = exception.to_long_message(SAMPLE_SOURCE, SAMPLE_SOURCE_PATH)
    assert isinstance(message, str)

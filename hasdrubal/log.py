from logging import DEBUG, FileHandler, Formatter, getLogger, WARN
from pathlib import Path

_log_file_path = Path(__file__).parent.parent.joinpath("hasdrubal.log").resolve()

if not _log_file_path.exists():
    _log_file_path.parent.mkdir(parents=True, exist_ok=True)
    _log_file_path.touch(exist_ok=True)

LOGGER_LEVEL = WARN if __debug__ else DEBUG
_formatter = Formatter(fmt="[%(levelname)s] %(message)s")

_handler = FileHandler(filename=str(_log_file_path))
_handler.setFormatter(_formatter)

logger = getLogger()
logger.addHandler(_handler)
logger.setLevel(LOGGER_LEVEL)

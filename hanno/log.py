from logging import FileHandler, Formatter, getLogger, INFO
from pathlib import Path

_log_file = Path(__file__).parent.parent.joinpath("hasdrubal.log").resolve()
# NOTE: Be careful with this value, it depends on the path to this file
_log_file.touch()

LOGGER_LEVEL = INFO

_handler = FileHandler(_log_file, delay=True, mode="w")
_formatter = Formatter(fmt="[%(levelname)s] %(message)s")
_handler.setFormatter(_formatter)

logger = getLogger()
logger.addHandler(_handler)
logger.setLevel(LOGGER_LEVEL)

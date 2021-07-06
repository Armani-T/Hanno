# pylint: disable=C0413, W0611, W0612, E0401
from sys import path
from pathlib import Path

APP_PATH = str(Path(__file__).parent.parent / "hasdrubal")
path.insert(0, APP_PATH)

import args
import errors
import lex

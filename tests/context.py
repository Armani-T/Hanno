from sys import path
from pathlib import Path

APP_PATH = str(Path(__file__).parent.parent / "hasdrubal")
path.insert(0, APP_PATH)

import errors
import lex

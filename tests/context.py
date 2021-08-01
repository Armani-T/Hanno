# pylint: disable=C0413, W0611, W0612, E0401
from pathlib import Path
from sys import path

APP_PATH = str(Path(__file__).parent.parent / "hasdrubal")
path.insert(0, APP_PATH)


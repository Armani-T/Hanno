from pathlib import Path
from sys import path

APP_PATH = Path(__file__).parent.parent / "hanno"
if APP_PATH.exists():
    path.insert(0, str(APP_PATH))
else:
    raise RuntimeError(f"Application wasn't found at {APP_PATH}")

import codegen

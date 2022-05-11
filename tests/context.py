from pathlib import Path
from sys import path

APP_PATH = Path(__file__).parent.parent / "hanno"
if APP_PATH.exists():
    path.insert(0, str(APP_PATH))
else:
    raise RuntimeError(f"Application wasn't found at {APP_PATH}")

import args
import codegen
import errors
import lex
import parse
import format as pprint
import run
import scope
import type_inference
from asts import base, lowered, typed, visitor, types_ as types
from visitors import ast_sorter, constant_folder, inline_expander, string_expander

base.ASTNode.__repr__ = lambda node: node.visit(pprint.ASTPrinter())
typed.TypedASTNode.__repr__ = lambda node: node.visit(pprint.TypedASTPrinter())
lowered.LoweredASTNode.__repr__ = lambda node: node.visit(pprint.LoweredASTPrinter())

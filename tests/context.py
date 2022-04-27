# pylint: disable=C0413, W0611, W0612, E0401
from pathlib import Path
from sys import path

APP_PATH = str(Path(__file__).parent.parent / "hanno")
path.insert(0, APP_PATH)

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
from visitors import (
    ast_sorter,
    constant_folder,
    inline_expander,
    string_expander,
    type_var_resolver,
)

base.ASTNode.__repr__ = lambda node: node.visit(pprint.ASTPrinter())
types.Type.__repr__ = pprint.show_type
typed.TypedASTNode.__repr__ = lambda node: node.visit(pprint.TypedASTPrinter())
lowered.LoweredASTNode.__repr__ = lambda node: node.visit(pprint.LoweredASTPrinter())

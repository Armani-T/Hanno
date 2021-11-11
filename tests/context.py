# pylint: disable=C0413, W0611, W0612, E0401
from pathlib import Path
from sys import path

APP_PATH = str(Path(__file__).parent.parent / "hasdrubal")
path.insert(0, APP_PATH)

import args
from asts import base, lowered, typed, types_ as types
import ast_sorter as sorter
import codegen
import constant_folder
import errors
import lex
import parse_ as parse
import pprint_
import scope
import type_inferer
import type_var_resolver

base.ASTNode.__repr__ = lambda node: node.visit(pprint_.ASTPrinter())
types.Type.__repr__ = lambda node: pprint_.show_type(node, True)
typed.TypedASTNode.__repr__ = lambda node: node.visit(pprint_.TypedASTPrinter())
lowered.LoweredASTNode.__repr__ = lambda node: node.visit(pprint_.LoweredASTPrinter())

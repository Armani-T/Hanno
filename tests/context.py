# pylint: disable=C0413, W0611, W0612, E0401
from pathlib import Path
from sys import path

APP_PATH = str(Path(__file__).parent.parent / "hasdrubal")
path.insert(0, APP_PATH)

import args
from asts import base, lowered, typed, visitor, types_ as types
import ast_sorter as sorter
import codegen
import constant_folder
import errors
import inline_expander
import lex
import parse
import pprint_ as pprint
import scope
import type_inferer
import type_var_resolver

base.ASTNode.__repr__ = lambda node: f"({node.visit(pprint.ASTPrinter())})"
types.Type.__repr__ = pprint.show_type
typed.TypedASTNode.__repr__ = lambda node: f"({node.visit(pprint.TypedASTPrinter())})"
lowered.FuncCall.__repr__ = lambda node: pprint.LoweredASTPrinter().visit_func_call(
    node
)
lowered.Function.__repr__ = lambda node: pprint.LoweredASTPrinter().visit_function(node)
lowered.NativeOperation.__repr__ = (
    lambda node: pprint.LoweredASTPrinter().visit_native_operation(node)
)

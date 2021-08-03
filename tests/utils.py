# pylint: disable=W0612
from context import base, pprint_, types

base.ASTNode.__repr__ = lambda node: node.visit(pprint_.ASTPrinter())
types.Type.__repr__ = lambda node: pprint_.show_type(node, True)

SAMPLE_SOURCE = "let l = [1, 2, 3] <> [4, 5, 6] in head(l)"
SAMPLE_SOURCE_PATH = __file__


class FakeNamespace:
    """
    This class is a dummy object for mocking references to attributes
    in the `argparse.namespace` class.
    """

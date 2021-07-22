from functools import reduce
from operator import or_
from typing import Sequence

from visitor import NodeVisitor
import ast_ as ast


def topological_sort(
    exprs: Sequence[ast.ASTNode],
    incoming: dict[ast.ASTNode, ast.Name],
    defintions: dict[ast.Name, ast.Define],
) -> Sequence[ast.ASTNode]:
    """
    Do a topological sort on the exprs inside of `ast_.Block`.

    Parameters
    ----------
    exprs: Sequence[ast_.ASTNode]
        The expressions that are supposed to be sorted.
    incoming: dict[ast_.ASTNode, ast_.Name]
        A mapping of expressions to the names that they require in order to run.
    defintions: dict[ast_.Name, ast_.Define]
        A mapping of names to their definition sites.

    Returns
    -------
    Sequence[ast_.ASTNode]
        The sorted expressions.
    """
    if len(exprs) < 2:
        return exprs

    incoming = {
        expr: [defintions[dep] for dep in deps if dep in defintions]
        for expr, deps in incoming.items()
    }
    incoming_count = {expr: len(incoming[expr]) for expr in exprs}
    outgoing = _generate_outgoing(incoming)
    ready = [node for node, dep_size in incoming_count.items() if dep_size == 0]
    sorted_ = []

    while ready:
        node = ready.pop()
        sorted_.append(node)
        endpoints: Sequence[ast.ASTNode] = outgoing.get(node, ())
        for endpoint in endpoints:
            incoming_count[endpoint] -= 1
            if incoming_count[endpoint] == 0:
                ready.append(endpoint)

    return sorted_


def _generate_outgoing(
    incoming: dict[ast.ASTNode, ast.ASTNode],
) -> dict[ast.ASTNode, set[ast.ASTNode]]:
    results = {}
    for key, values in incoming.items():
        for value in values:
            existing = results.get(value, ())
            results[value] = (key, *existing)
    return results


class TopologicalSorter(NodeVisitor[set[ast.Name]]):
    """
    Reorder all blocks within the AST so that all expressions inside
    it are in a position where  all the name sthat they depend on are
    already defined.

    Warnings
    --------
    - This class will change the order of `ast_.Block` nodes.
    - This class can't handle recursive definitions yet.
    """

    def __init__(self) -> None:
        self._definitions: dict[ast.Name, ast.ASTNode] = {}

    def visit_block(self, node: ast.Block) -> set[ast.Name]:
        body = (node.first, *node.rest)
        dep_map: dict[ast.ASTNode, set[ast.Name]] = {}
        total_deps: set[ast.Name] = set()
        prev_definitions = self._definitions
        self._definitions = {}
        for expr in body:
            node_deps = expr.visit(self)
            dep_map[expr] = node_deps
            total_deps |= node_deps

        first, *rest = topological_sort(body, dep_map, self._definitions)
        node.first = first
        node.rest = rest
        self._definitions = prev_definitions
        return total_deps

    def visit_cond(self, node: ast.Cond) -> set[ast.Name]:
        body = (node.pred, node.cons, node.else_)
        return reduce(or_, map(self.run, body), set())

    def visit_define(self, node: ast.Define) -> set[ast.Name]:
        self._definitions[node.target] = node
        body_deps = set() if node.body is None else node.body.visit(self)
        return node.value.visit(self) | body_deps

    def visit_func_call(self, node: ast.FuncCall) -> set[ast.Name]:
        return node.caller.visit(self) | node.callee.visit(self)

    def visit_function(self, node: ast.Function) -> set[ast.Name]:
        return node.body.visit(self) - {node.param}

    def visit_name(self, node: ast.Name) -> set[ast.Name]:
        return {node}

    def visit_scalar(self, node: ast.Scalar) -> set[ast.Name]:
        return set()

    def visit_type(self, node: ast.Type) -> set[ast.Name]:
        return set()

    def visit_vector(self, node: ast.Vector) -> set[ast.Name]:
        return reduce(or_, map(self.run, node.elements), set())

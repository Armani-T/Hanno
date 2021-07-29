from functools import reduce
from operator import or_
from typing import Iterable, Mapping, Sequence

from visitor import NodeVisitor
import ast_ as ast


def topological_sort(node: ast.ASTNode) -> ast.ASTNode:
    """
    Do a topological sort on expressions inside of blocks in the AST
    such that they always come after the definitions of names that they
    use.

    Warnings
    --------
    - This function cannot handle recursive definitions.

    Parameters
    ----------
    node: ast_.ASTNode
        The expressions that are supposed to be sorted.

    Returns
    -------
    ast_.ASTNode
        The AST containing sorted blocks.
    """
    sorter = TopologicalSorter()
    new_node, _ = sorter.run(node)
    return new_node


def topological_sort_exprs(
    exprs: Sequence[ast.ASTNode],
    incoming: Mapping[ast.ASTNode, Iterable[ast.Name]],
    definitions: Mapping[ast.Name, ast.Define],
) -> Sequence[ast.ASTNode]:
    if len(exprs) < 2:
        return exprs

    incoming_defs: dict[ast.ASTNode, list[ast.ASTNode]] = {
        expr: [definitions[dep] for dep in deps if dep in definitions]
        for expr, deps in incoming.items()
    }
    outgoing = _generate_outgoing(incoming_defs)
    incoming_count = {key: len(value) for key, value in incoming_defs.items()}
    ready = [node for node, dep_size in incoming_count.items() if dep_size == 0]
    sorted_ = []

    while ready:
        node = ready.pop()
        sorted_.append(node)
        for endpoint in outgoing.get(node, ()):
            incoming_count[endpoint] -= 1
            if incoming_count[endpoint] == 0:
                ready.append(endpoint)

    return sorted_


def _generate_outgoing(
    incoming: Mapping[ast.ASTNode, Iterable[ast.ASTNode]]
) -> Mapping[ast.ASTNode, Sequence[ast.ASTNode]]:
    results: dict[ast.ASTNode, tuple[ast.ASTNode, ...]] = {}
    for key, values in incoming.items():
        for value in values:
            existing = results.get(value, ())
            results[value] = (key, *existing)
    return results


class TopologicalSorter(NodeVisitor[tuple[ast.ASTNode, set[ast.Name]]]):
    """
    Reorder all blocks within the AST so that all expressions inside
    it are in a position where  all the names that they depend on are
    already defined.

    Warnings
    --------
    - This class will change the order of `ast_.Block` nodes.
    - This class can't handle recursive definitions yet.
    """

    def __init__(self) -> None:
        self._definitions: dict[ast.Name, ast.Define] = {}

    def visit_block(self, node: ast.Block) -> tuple[ast.ASTNode, set[ast.Name]]:
        dep_map: dict[ast.ASTNode, set[ast.Name]] = {}
        total_deps: set[ast.Name] = set()
        prev_definitions = self._definitions
        self._definitions = {}
        new_body = []
        for expr in (node.first, *node.rest):
            new_expr, node_deps = expr.visit(self)
            new_body.append(new_expr)
            dep_map[expr] = node_deps
            total_deps |= node_deps

        sorted_exprs = topological_sort_exprs(new_body, dep_map, self._definitions)
        self._definitions = prev_definitions
        return ast.Block(node.span, sorted_exprs), total_deps

    def visit_cond(self, node: ast.Cond) -> tuple[ast.ASTNode, set[ast.Name]]:
        _, pred_deps = node.pred.visit(self)
        _, cons_deps = node.cons.visit(self)
        _, else_deps = node.else_.visit(self)
        return node, pred_deps | cons_deps | else_deps

    def visit_define(self, node: ast.Define) -> tuple[ast.ASTNode, set[ast.Name]]:
        self._definitions[node.target] = node
        _, value_deps = node.value.visit(self)
        _, body_deps = (None, set()) if node.body is None else node.body.visit(self)
        return node, value_deps | body_deps

    def visit_func_call(self, node: ast.FuncCall) -> tuple[ast.ASTNode, set[ast.Name]]:
        _, caller_deps = node.caller.visit(self)
        _, callee_deps = node.callee.visit(self)
        return node, caller_deps | callee_deps

    def visit_function(self, node: ast.Function) -> tuple[ast.ASTNode, set[ast.Name]]:
        _, body_deps = node.body.visit(self)
        body_deps.discard(node.param)
        return node, body_deps

    def visit_name(self, node: ast.Name) -> tuple[ast.ASTNode, set[ast.Name]]:
        return node, {node}

    def visit_scalar(self, node: ast.Scalar) -> tuple[ast.ASTNode, set[ast.Name]]:
        return node, set()

    def visit_type(self, node: ast.Type) -> tuple[ast.ASTNode, set[ast.Name]]:
        return node, set()

    def visit_vector(self, node: ast.Vector) -> tuple[ast.ASTNode, set[ast.Name]]:
        sections = (elem.visit(self)[1] for elem in node.elements)
        return node, reduce(or_, sections, set())

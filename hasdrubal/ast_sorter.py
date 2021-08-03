from functools import reduce
from operator import or_
from typing import Iterable, Mapping, Sequence

from asts.types import Type
from asts import base
from visitor import NodeVisitor


def topological_sort(node: base.ASTNode) -> base.ASTNode:
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
    exprs: Sequence[base.ASTNode],
    incoming: Mapping[base.ASTNode, Iterable[base.Name]],
    definitions: Mapping[base.Name, base.Define],
) -> Sequence[base.ASTNode]:
    if len(exprs) < 2:
        return exprs

    incoming_defs: dict[base.ASTNode, list[base.ASTNode]] = {
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
    incoming: Mapping[base.ASTNode, Iterable[base.ASTNode]]
) -> Mapping[base.ASTNode, Sequence[base.ASTNode]]:
    results: dict[base.ASTNode, tuple[base.ASTNode, ...]] = {}
    for key, values in incoming.items():
        for value in values:
            existing = results.get(value, ())
            results[value] = (key, *existing)
    return results


class TopologicalSorter(NodeVisitor[tuple[base.ASTNode, set[base.Name]]]):
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
        self._definitions: dict[base.Name, base.Define] = {}

    def visit_block(self, node: base.Block) -> tuple[base.ASTNode, set[base.Name]]:
        dep_map: dict[base.ASTNode, set[base.Name]] = {}
        total_deps: set[base.Name] = set()
        prev_definitions = self._definitions
        self._definitions = {}
        new_body = []
        for expr in node.body():
            new_expr, node_deps = expr.visit(self)
            new_body.append(new_expr)
            dep_map[expr] = node_deps
            total_deps |= node_deps

        sorted_exprs = topological_sort_exprs(new_body, dep_map, self._definitions)
        self._definitions = prev_definitions
        return base.Block(node.span, sorted_exprs), total_deps

    def visit_cond(self, node: base.Cond) -> tuple[base.ASTNode, set[base.Name]]:
        _, pred_deps = node.pred.visit(self)
        _, cons_deps = node.cons.visit(self)
        _, else_deps = node.else_.visit(self)
        return node, pred_deps | cons_deps | else_deps

    def visit_define(self, node: base.Define) -> tuple[base.ASTNode, set[base.Name]]:
        self._definitions[node.target] = node
        _, value_deps = node.value.visit(self)
        _, body_deps = (None, set()) if node.body is None else node.body.visit(self)
        all_deps = value_deps | body_deps
        all_deps.discard(node.target)
        # NOTE: I'm removing the target because of recursive definitions
        return node, all_deps

    def visit_func_call(
        self, node: base.FuncCall
    ) -> tuple[base.ASTNode, set[base.Name]]:
        _, caller_deps = node.caller.visit(self)
        _, callee_deps = node.callee.visit(self)
        return node, caller_deps | callee_deps

    def visit_function(
        self, node: base.Function
    ) -> tuple[base.ASTNode, set[base.Name]]:
        _, body_deps = node.body.visit(self)
        body_deps.discard(node.param)
        return node, body_deps

    def visit_name(self, node: base.Name) -> tuple[base.ASTNode, set[base.Name]]:
        return node, {node}

    def visit_scalar(self, node: base.Scalar) -> tuple[base.ASTNode, set[base.Name]]:
        return node, set()

    def visit_type(self, node: Type) -> tuple[base.ASTNode, set[base.Name]]:
        return node, set()

    def visit_vector(self, node: base.Vector) -> tuple[base.ASTNode, set[base.Name]]:
        sections = (elem.visit(self)[1] for elem in node.elements)
        return node, reduce(or_, sections, set())

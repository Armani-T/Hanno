from functools import reduce
from operator import or_
from typing import Iterable, Mapping, MutableMapping, Sequence, Set, Tuple, Union

from asts import base, types_ as types, visitor

Incoming = Mapping[base.ASTNode, Iterable[base.ASTNode]]
Outgoing = Mapping[base.ASTNode, Sequence[base.ASTNode]]
Names = Union[base.Name, types.TypeName]


def topological_sort(node: base.ASTNode) -> base.ASTNode:
    """
    Do a topological sort on expressions inside of blocks in the AST
    such that they always come after the definitions of names that they
    use.

    Warnings
    --------
    - This function cannot handle mutually recursive definitions.

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
    """Run a topological sort on the expressions within a block."""
    if len(exprs) < 2:
        return exprs

    incoming_defs: Mapping[base.ASTNode, Sequence[base.ASTNode]] = {
        expr: [definitions[dep] for dep in deps if dep in definitions]
        for expr, deps in incoming.items()
    }
    outgoing = generate_outgoing(incoming_defs)
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


def generate_outgoing(incoming: Incoming) -> Outgoing:
    """
    Create a map from definitions to all the nodes that depend on them.

    Parameters
    ----------
    incoming: Mapping[base.ASTNode, Iterable[base.ASTNode]]
        A map from AST nodes to the definitions they depend on.

    Returns
    -------
    Mapping[base.ASTNode, Sequence[base.ASTNode]]
        A map of definitions to all the nodes that depend on them.
    """
    results: MutableMapping[base.ASTNode, Tuple[base.ASTNode, ...]] = {}
    for key, values in incoming.items():
        for value in values:
            existing = results.get(value, ())
            results[value] = (key, *existing)
    return results


def find_free_names(pattern: base.Pattern) -> Set[base.Name]:
    """Find all the names that will generate bindings in a pattern."""
    if isinstance(pattern, base.FreeName):
        return {base.Name(pattern.span, pattern.value)}
    if isinstance(pattern, base.PairPattern):
        return find_free_names(pattern.first) | find_free_names(pattern.second)
    if isinstance(pattern, base.ListPattern):
        rest = (
            set()
            if pattern.rest is None
            else {base.Name(pattern.rest.span, pattern.rest.value)}
        )
        return rest | reduce(
            or_,
            map(find_free_names, pattern.initial_patterns),
            set(),
        )
    return set()


def find_pinned_names(pattern: base.Pattern) -> Set[base.Name]:
    """
    Find all the names that depend on external bindings in a pattern.

    Parameters
    ----------
    pattern: base.Pattern
        The entire pattern.

    Returns
    -------
    Set[base.Name]
        The names that are formed by external bindings.
    """
    if isinstance(pattern, base.PinnedName):
        return {base.Name(pattern.span, pattern.value)}
    if isinstance(pattern, base.PairPattern):
        return find_free_names(pattern.first) | find_free_names(pattern.second)
    if isinstance(pattern, base.ListPattern):
        rest = (
            set()
            if pattern.rest is None
            else {base.Name(pattern.rest.span, pattern.rest.value)}
        )
        return rest | reduce(
            or_,
            map(find_free_names, pattern.initial_patterns),
            set(),
        )
    return set()


class TopologicalSorter(visitor.BaseASTVisitor[Tuple[base.ASTNode, Set[Names]]]):
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
        self._definitions: MutableMapping[base.Name, base.Define] = {}

    def visit_annotation(
        self, node: base.Annotation
    ) -> Tuple[base.Annotation, Set[Names]]:
        _, type_names = node.type_.visit(self)
        return node, type_names

    def visit_apply(self, node: base.Apply) -> Tuple[base.ASTNode, Set[Names]]:
        new_func, func_deps = node.func.visit(self)
        new_args, arg_deps = node.arg.visit(self)
        return base.Apply(node.span, new_func, new_args), func_deps | arg_deps

    def visit_block(self, node: base.Block) -> Tuple[base.ASTNode, Set[Names]]:
        dep_map: MutableMapping[base.ASTNode, Set[Names]] = {}
        total_deps: Set[Names] = set()
        prev_definitions = self._definitions
        self._definitions = {}
        new_body = []
        for expr in node.body:
            new_expr, node_deps = expr.visit(self)
            new_body.append(new_expr)
            dep_map[expr] = node_deps
            total_deps |= node_deps

        sorted_exprs = topological_sort_exprs(new_body, dep_map, self._definitions)
        self._definitions = prev_definitions
        return base.Block(node.span, sorted_exprs), total_deps

    def visit_cond(self, node: base.Cond) -> Tuple[base.ASTNode, Set[Names]]:
        new_pred, pred_deps = node.pred.visit(self)
        new_cons, cons_deps = node.cons.visit(self)
        new_else, else_deps = node.else_.visit(self)
        return (
            base.Cond(node.span, new_pred, new_cons, new_else),
            pred_deps | cons_deps | else_deps,
        )

    def visit_define(self, node: base.Define) -> Tuple[base.ASTNode, Set[Names]]:
        new_value, value_deps = node.value.visit(self)
        free_names = find_free_names(node.target)
        deps = value_deps - free_names
        new_node = base.Define(node.span, node.target, new_value)
        for name in free_names:
            self._definitions[name] = new_node

        return new_node, deps

    def visit_function(self, node: base.Function) -> Tuple[base.ASTNode, Set[Names]]:
        new_body, body_deps = node.body.visit(self)
        deps = body_deps - find_free_names(node.param)
        return base.Function(node.span, node.param, new_body), deps

    def visit_impl(self, node: base.Impl) -> Tuple[base.ASTNode, Set[Names]]:
        names = {node.parent}
        for method in node.methods:
            _, method_names = method.visit(self)
            names |= method_names
        return node, names

    def visit_list(self, node: base.List) -> Tuple[base.ASTNode, Set[Names]]:
        elements = []
        sections = []
        for elem in node.elements:
            new_elem, new_section = elem.visit(self)
            elements.append(new_elem)
            sections.append(new_section)
        return base.List(node.span, elements), reduce(or_, sections, set())

    def visit_match(self, node: base.Match) -> Tuple[base.ASTNode, Set[Names]]:
        subject, subject_deps = node.subject.visit(self)
        case_deps = set()
        cases = []
        for pred, cons in node.cases:
            _, pred_deps = pred.visit(self)
            new_cons, cons_deps = cons.visit(self)
            cases.append((pred, new_cons))
            case_deps |= pred_deps | cons_deps
        return base.Match(node.span, subject, cases), subject_deps | case_deps

    def visit_pair(self, node: base.Pair) -> Tuple[base.ASTNode, Set[Names]]:
        new_first, first_deps = node.first.visit(self)
        new_second, second_deps = node.second.visit(self)
        return base.Pair(node.span, new_first, new_second), first_deps | second_deps

    def visit_pattern(self, node: base.Pattern) -> Tuple[base.ASTNode, Set[Names]]:
        return node, find_pinned_names(node)

    def visit_name(self, node: base.Name) -> Tuple[base.ASTNode, Set[Names]]:
        return node, {node}

    def visit_scalar(self, node: base.Scalar) -> Tuple[base.ASTNode, Set[Names]]:
        return node, set()

    def visit_trait(self, node: base.Trait) -> Tuple[base.ASTNode, Set[Names]]:
        names = set(node.parents)
        for method in node.methods:
            _, method_names = method.visit(self)
            names |= method_names
        return node, names

    def visit_type(self, node: types.Type) -> Tuple[base.ASTNode, Set[Names]]:
        if isinstance(node, types.TypeApply):
            _, caller_names = node.caller.visit(self)
            _, callee_names = node.callee.visit(self)
            return node, caller_names | callee_names
        if isinstance(node, types.TypeName):
            return node, {node}
        if isinstance(node, types.TypeScheme):
            _, actual_type_names = node.actual_type.visit(self)
            return node, actual_type_names
        if isinstance(node, types.TypeVar):
            return node, set()

    def visit_unit(self, node: base.Unit) -> Tuple[base.ASTNode, Set[Names]]:
        return node, set()

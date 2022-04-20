from asts import typed
from asts.base import Pattern
from asts.types_ import Type
from asts.visitors import TypedASTVisitor


class ExhaustivenessChecker(TypedASTVisitor[None]):
    def visit_apply(self, node: typed.Apply) -> None:
        ...

    def visit_block(self, node: typed.Block) -> None:
        ...

    def visit_cond(self, node: typed.Cond) -> None:
        ...

    def visit_define(self, node: typed.Define) -> None:
        ...

    def visit_function(self, node: typed.Function) -> None:
        ...

    def visit_list(self, node: typed.List) -> None:
        ...

    def visit_match(self, node: typed.Match) -> None:
        ...

    def visit_pair(self, node: typed.Pair) -> None:
        ...

    def visit_name(self, node: typed.Name) -> None:
        ...

    def visit_scalar(self, node: typed.Scalar) -> None:
        ...

    def visit_type(self, node: Type) -> None:
        ...

    def visit_unit(self, node: typed.Unit) -> None:
        ...

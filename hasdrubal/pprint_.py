from ast_ import FuncType, GenericType, TypeScheme, TypeVar
from visitor import NodeVisitor
import ast_ as ast


class ASTPrinter(NodeVisitor[str]):
    """This visitor produces a string version of the entire AST."""

    def __init__(self) -> None:
        self.indent_level: int = -1

    def visit_block(self, node: ast.Block) -> str:
        body = (node.first, *node.rest)
        self.indent_level += 1
        preface = f"\n{'  ' * self.indent_level}"
        result = preface + preface.join((expr.visit(self) for expr in body))
        self.indent_level -= 1
        return result

    def visit_cond(self, node: ast.Cond) -> str:
        pred = node.pred.visit(self)
        cons = node.cons.visit(self)
        else_ = node.else_.visit(self)
        return f"if {pred} then {cons} else {else_}"

    def visit_define(self, node: ast.Define) -> str:
        target = node.target.visit(self)
        value = node.value.visit(self)
        body = "" if node.body is None else f" in {node.body.visit(self)}"
        return f"let {target} = {value}{body}"

    def visit_func_call(self, node: ast.FuncCall) -> str:
        return f"{node.caller.visit(self)}( {node.callee.visit(self)} )"

    def visit_function(self, node: ast.Function) -> str:
        return f"\\{node.param.visit(self)} -> {node.body.visit(self)}"

    def visit_name(self, node: ast.Name) -> str:
        return node.value

    def visit_scalar(self, node: ast.Scalar) -> str:
        return node.value_string

    def visit_type(self, node: ast.Type) -> str:
        if isinstance(node, TypeVar):
            return f"@{node.value}"
        if isinstance(node, FuncType):
            return f"{node.left.visit(self)} -> {node.right.visit(self)}"
        if isinstance(node, GenericType):
            result = node.base.visit(self)
            args = (
                f"[{' '.join(map(lambda n: n.visit(self), node.args))}]"
                if node.args
                else ""
            )
            return f"{result}{args}"
        if isinstance(node, TypeScheme):
            bound = [type_.visit(self) for type_ in node.bound_types]
            return f"∀ {', '.join(bound)} • {node.type_.visit(self)}"

        raise TypeError(
            f"{node} is an invalid subtype of nodes.Type, it is {type(node)}"
        )

    def visit_vector(self, node: ast.Vector) -> str:
        bracket = {
            ast.VectorTypes.LIST: lambda string: f"[{string}]",
            ast.VectorTypes.TUPLE: lambda string: f"({string})",
        }[node.vec_type]
        return bracket(", ".join((elem.visit(self) for elem in node.elements)))


class TypedASTPrinter(ASTPrinter):
    """
    This visitor produces a string version of the entire AST with full
    type annotations.

    Warnings
    --------
    This visitor assumes that the `type_` annotation is never `None`.
    """

    def visit_block(self, node: ast.Block) -> str:
        result = node.first.visit(self)
        if node.rest:
            self.indent_level += 1
            preface = f"\n{'  ' * self.indent_level}"
            result = (
                f"{preface}{result}{preface}"
                f"{preface.join((expr.visit(self) for expr in node.rest))}"
                f"{preface}# type: {node.type_.visit(self)}"
            )
            self.indent_level -= 1
        return result

    def visit_cond(self, node: ast.Cond) -> str:
        type_ = node.type_.visit(self)
        return f"({super().visit_cond(node)}) :: {type_}"

    def visit_define(self, node: ast.Define) -> str:
        target = node.target.visit(self)
        value = ASTPrinter().run(node.value)
        first = f"let {target} :: {node.type_.visit(self)} = {value}"
        if node.body is not None:
            body = node.body.visit(self)
            return f"({first} in {body}) :: {node.type_.visit(self)}"
        return first

    def visit_func_call(self, node: ast.FuncCall) -> str:
        type_ = node.type_.visit(self)
        return f"({super().visit_func_call(node)}) :: {type_}"

    def visit_function(self, node: ast.Function) -> str:
        type_ = node.type_.visit(self)
        return f"(\\{node.param.visit(self)} -> {node.body.visit(self)}) :: {type_}"

    def visit_scalar(self, node: ast.Scalar) -> str:
        return node.value_string

    def visit_vector(self, node: ast.Vector) -> str:
        return f"{super().visit_vector(node)} :: {node.type_.visit(self)}"

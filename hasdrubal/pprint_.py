from functools import lru_cache
from typing import List, MutableMapping

from asts import base, lowered, typed, visitor
from asts.types_ import Type, TypeApply, TypeName, TypeScheme, TypeVar

usable_letters = list("zyxwvutsrqponmlkjihgfedcba")
available_letters = usable_letters.copy()
var_names: MutableMapping[int, str] = {}


@lru_cache(maxsize=256)
def show_type_var(type_var: TypeVar) -> str:
    """
    Represent a type var as a string (preferably an alphabetic letter).

    Parameters
    ----------
    type_var: TypeVar
        The type var to be represented.

    Returns
    -------
    str
        The string representation of the type var.
    """
    try:
        number = int(type_var.value)
        if number in var_names:
            return var_names[number]

        letter = available_letters.pop()
        var_names[number] = letter
        return letter

    except IndexError:
        number = int(type_var.value)
        letter = usable_letters[number % len(usable_letters)]
        var_names[number] = f"{letter}{number - len(usable_letters)}"
        return var_names[number]

    except ValueError:
        return type_var.value


def show_type_apply(type_apply: TypeApply) -> str:
    """
    Represent a type application as a user-readable string.

    Parameters
    ----------
    type_apply: TypeApply
        The type application to be represented.

    Returns
    -------
    str
        The representation of the type application.
    """
    type_: Type = type_apply
    args: List[str] = []
    while isinstance(type_, TypeApply):
        args.append(show_type(type_.callee, True))
        type_ = type_.caller

    if len(args) == 2 and isinstance(type_, TypeName) and not type_.value.isalnum():
        second = args[0][1:-1] if args[0].startswith("(") else args[0]
        return f"{args[1]} {type_.value} {second}"
    return f"{show_type(type_)}[{', '.join(args)}]"


def show_type(type_: Type, bracket: bool = False) -> str:
    """
    Turn `type_` into a string representation.

    Parameters
    ----------
    type_: Type
        The type to turn into a string.
    bracket: bool = True
        Whether to parenthesise function type and type scheme
        representations.

    Returns
    -------
    str
        The resulting type representation.
    """
    if isinstance(type_, TypeApply):
        result = show_type_apply(type_)
        return f"({result})" if bracket else result
    if isinstance(type_, TypeName):
        return type_.value
    if isinstance(type_, TypeScheme):
        bound = map(show_type, type_.bound_types)
        result = f"∀ {', '.join(bound)} • {show_type(type_.actual_type)}"
        return f"({result})" if bracket else result
    if isinstance(type_, TypeVar):
        return show_type_var(type_)
    raise TypeError(f"{type(type_)} is an invalid subtype of nodes.Type.")


class ASTPrinter(visitor.BaseASTVisitor[str]):
    """This visitor produces a string version of the entire AST."""

    def __init__(self) -> None:
        self.indent_level: int = -1
        self.indent_char: str = "  "

    def visit_block(self, node: base.Block) -> str:
        self.indent_level += 1
        preface = f"\n{self.indent_char * self.indent_level}"
        result = preface + preface.join((expr.visit(self) for expr in node.body))
        self.indent_level -= 1
        return result

    def visit_cond(self, node: base.Cond) -> str:
        pred = node.pred.visit(self)
        cons = node.cons.visit(self)
        else_ = node.else_.visit(self)
        return f"if {pred} then {cons} else {else_}"

    def visit_define(self, node: base.Define) -> str:
        return f"let {node.target.visit(self)} = {node.value.visit(self)}"

    def visit_func_call(self, node: base.FuncCall) -> str:
        return f"{node.caller.visit(self)}( {node.callee.visit(self)} )"

    def visit_function(self, node: base.Function) -> str:
        return f"\\{node.param.visit(self)} -> {node.body.visit(self)}"

    def visit_name(self, node: base.Name) -> str:
        return node.value

    def visit_scalar(self, node: base.Scalar) -> str:
        return str(node.value)

    def visit_type(self, node: Type) -> str:
        return show_type(node)

    def visit_vector(self, node: base.Vector) -> str:
        bracket = {
            base.VectorTypes.LIST: lambda string: f"[{string}]",
            base.VectorTypes.TUPLE: lambda string: f"({string})",
        }[node.vec_type]
        return bracket(", ".join((elem.visit(self) for elem in node.elements)))


class TypedASTPrinter(visitor.TypedASTVisitor[str]):
    """
    This visitor produces a string version of the entire AST with full
    type annotations.

    Warnings
    --------
    This visitor assumes that the `type_` annotation is never `None`.
    """

    def __init__(self) -> None:
        self.indent_level: int = -1

    def visit_block(self, node: typed.Block) -> str:
        self.indent_level += 1
        preface = f"\n{'  ' * self.indent_level}"
        result = (
            f"{preface}{preface.join((expr.visit(self) for expr in node.body))}"
            f"{preface}# type: {node.type_.visit(self)}"
        )
        self.indent_level -= 1
        return result

    def visit_cond(self, node: typed.Cond) -> str:
        type_ = node.type_.visit(self)
        return f"({super().visit_cond(node)}) :: {type_}"

    def visit_define(self, node: typed.Define) -> str:
        target = node.target.visit(self)
        value = node.value.visit(self)
        return f"let {target} = {value}"

    def visit_func_call(self, node: typed.FuncCall) -> str:
        type_ = node.type_.visit(self)
        return f"({super().visit_func_call(node)}) :: {type_}"

    def visit_function(self, node: typed.Function) -> str:
        type_ = node.type_.visit(self)
        return f"(\\{node.param.visit(self)} -> {node.body.visit(self)}) :: {type_}"

    def visit_name(self, node: typed.Name) -> str:
        return f"{node.value} :: {node.type_.visit(self)}"

    def visit_scalar(self, node: typed.Scalar) -> str:
        return str(node.value)

    def visit_type(self, node: Type) -> str:
        return show_type(node)

    def visit_vector(self, node: typed.Vector) -> str:
        return f"{super().visit_vector(node)} :: {node.type_.visit(self)}"


class LoweredASTPrinter(visitor.LoweredASTVisitor[str]):
    """This visitor produces a string version of the lowered AST."""

    def __init__(self) -> None:
        self.indent_level: int = -1

    def visit_block(self, node: lowered.Block) -> str:
        self.indent_level += 1
        preface = f"\n{'  ' * self.indent_level}"
        result = preface + preface.join((expr.visit(self) for expr in node.body))
        self.indent_level -= 1
        return result

    def visit_cond(self, node: lowered.Cond) -> str:
        pred = node.pred.visit(self)
        cons = node.cons.visit(self)
        else_ = node.else_.visit(self)
        return f"if {pred} then {cons} else {else_}"

    def visit_define(self, node: lowered.Define) -> str:
        return f"let {node.target.visit(self)} = {node.value.visit(self)}"

    def visit_func_call(self, node: lowered.FuncCall) -> str:
        caller = node.func.visit(self)
        args = ", ".join(map(self.run, node.args))
        return f"{caller}({args})"

    def visit_function(self, node: lowered.Function) -> str:
        params = ", ".join(map(self.run, node.params))
        return f"\\{params} -> {node.body.visit(self)}"

    def visit_name(self, node: lowered.Name) -> str:
        return node.value

    def visit_native_operation(self, node: lowered.NativeOperation) -> str:
        op = node.operation.value
        left = node.left.visit(self)
        return (
            f"{op}{left}"
            if node.right is None
            else f"{left} {op} {node.right.visit(self)}"
        )

    def visit_scalar(self, node: lowered.Scalar) -> str:
        return str(node.value)

    def visit_vector(self, node: lowered.Vector) -> str:
        bracket = {
            base.VectorTypes.LIST: lambda string: f"[{string}]",
            base.VectorTypes.TUPLE: lambda string: f"({string})",
        }[node.vec_type]
        return bracket(", ".join((elem.visit(self) for elem in node.elements)))

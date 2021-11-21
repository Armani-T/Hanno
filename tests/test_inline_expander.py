# pylint: disable=C0116
from typing import Collection

from pytest import mark

from context import lowered, inline_expander, scope, visitor


class NameFinder(visitor.LoweredASTVisitor[bool]):
    def __init__(self, *names: str) -> None:
        self.names: Collection[str] = names

    def visit_block(self, node: lowered.Block) -> bool:
        return any(map(self.run, node.body))

    def visit_cond(self, node: lowered.Cond) -> bool:
        return node.pred.visit(self) or node.cons.visit(self) or node.else_.visit(self)

    def visit_define(self, node: lowered.Define) -> bool:
        return (node.target.value in self.names) or node.value.visit(self)

    def visit_func_call(self, node: lowered.FuncCall) -> bool:
        return node.func.visit(self) or any(map(self.run, node.args))

    def visit_function(self, node: lowered.Function) -> bool:
        self_names = set(self.names)
        params = {param.value for param in node.params}
        original_names = self.names
        self.names = self_names - params
        result = node.body.visit(self)
        self.names = original_names
        return result

    def visit_name(self, node: lowered.Name) -> bool:
        return node.value in self.names

    def visit_native_operation(self, node: lowered.NativeOperation) -> bool:
        in_right = False if node.right is None else node.right.visit(self)
        return node.left.visit(self) or in_right

    def visit_scalar(self, node: lowered.Scalar) -> bool:
        return False

    def visit_vector(self, node: lowered.Vector) -> bool:
        return any(map(self.run, node.elements))


span = (0, 0)


collatz_func = lowered.Function(
    span,
    [lowered.Name(span, "n")],
    lowered.Cond(
        span,
        lowered.NativeOperation(
            span,
            lowered.OperationTypes.EQUAL,
            lowered.NativeOperation(
                span,
                lowered.OperationTypes.MOD,
                lowered.Name(span, "n"),
                lowered.Scalar(span, 2),
            ),
            lowered.Scalar(span, 2),
        ),
        lowered.NativeOperation(
            span,
            lowered.OperationTypes.DIV,
            lowered.Name(span, "n"),
            lowered.Scalar(span, 2),
        ),
        lowered.NativeOperation(
            span,
            lowered.OperationTypes.ADD,
            lowered.NativeOperation(
                span,
                lowered.OperationTypes.MUL,
                lowered.Scalar(span, 3),
                lowered.Name(span, "n"),
            ),
            lowered.Scalar(span, 1),
        ),
    ),
)
identity_func = lowered.Function(
    span, [lowered.Name(span, "x")], lowered.Name(span, "x")
)


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "funcs,defined,threshold,expected",
    (
        ([], (), 0, {}),
        ([], (), 100, {}),
        ([identity_func], [identity_func], 0, {identity_func: 1}),
    ),
)
def test_generate_scores(funcs, defined, threshold, expected):
    actual = inline_expander.generate_scores(funcs, defined, threshold)
    assert expected == actual


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "func,args,expected",
    (
        (
            identity_func,
            [lowered.Scalar(span, 1)],
            lowered.Scalar(span, 1),
        ),
        (
            lowered.Function(
                span,
                [
                    lowered.Name(span, "pred"),
                    lowered.Name(span, "cons"),
                    lowered.Name(span, "else_"),
                ],
                lowered.Cond(
                    span,
                    lowered.Name(span, "pred"),
                    lowered.Name(span, "cons"),
                    lowered.Name(span, "else_"),
                ),
            ),
            [
                lowered.Scalar(span, True),
                lowered.Scalar(span, 1),
                lowered.Scalar(span, 2),
            ],
            lowered.Cond(
                span,
                lowered.Scalar(span, True),
                lowered.Scalar(span, 1),
                lowered.Scalar(span, 2),
            ),
        ),
    ),
)
def test_inline_function(func, args, expected):
    name_finder = NameFinder(func.params)
    actual = inline_expander.inline_function(span, func, args)
    assert actual.span == span
    assert not name_finder.run(actual)
    assert expected == actual


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "tree,expected",
    (
        (lowered.Scalar(span, 1.25), 0),
        (lowered.Name(span, "map"), 0),
        (identity_func, 7),
        (
            lowered.Block(
                span,
                [
                    lowered.Define(
                        span,
                        lowered.Name(span, "x"),
                        lowered.Scalar(span, 24),
                    ),
                    lowered.Define(
                        span,
                        lowered.Name(span, "y"),
                        lowered.NativeOperation(
                            span,
                            lowered.OperationTypes.EXP,
                            lowered.Name(span, "x"),
                            lowered.Scalar(span, 2),
                        ),
                    ),
                    lowered.NativeOperation(
                        span,
                        lowered.OperationTypes.DIV,
                        lowered.Name(span, "x"),
                        lowered.Name(span, "y"),
                    ),
                ],
            ),
            15,
        ),
        (
            lowered.Define(
                span,
                lowered.Name(span, "collatz"),
                lowered.Function(
                    span,
                    [lowered.Name(span, "n")],
                    lowered.Cond(
                        span,
                        lowered.NativeOperation(
                            span,
                            lowered.OperationTypes.EQUAL,
                            lowered.NativeOperation(
                                span,
                                lowered.OperationTypes.MOD,
                                lowered.Name(span, "n"),
                                lowered.Scalar(span, 2),
                            ),
                            lowered.Scalar(span, 2),
                        ),
                        lowered.NativeOperation(
                            span,
                            lowered.OperationTypes.DIV,
                            lowered.Name(span, "n"),
                            lowered.Scalar(span, 2),
                        ),
                        lowered.NativeOperation(
                            span,
                            lowered.OperationTypes.ADD,
                            lowered.NativeOperation(
                                span,
                                lowered.OperationTypes.MUL,
                                lowered.Scalar(span, 3),
                                lowered.Name(span, "n"),
                            ),
                            lowered.Scalar(span, 1),
                        ),
                    ),
                ),
            ),
            22,
        ),
    ),
)
def test_scorer(tree, expected):
    scorer = inline_expander._Scorer()
    actual = scorer.run(tree)
    assert expected == actual


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "tree,expected_length,expected_defined_length",
    (
        (lowered.Vector.unit(span), 0, 0),
        (
            lowered.Block(
                span, [lowered.Define(span, lowered.Name(span, "id"), identity_func)]
            ),
            1,
            1,
        ),
        (
            lowered.Block(
                span,
                [
                    lowered.Cond(
                        span,
                        lowered.FuncCall(
                            span,
                            lowered.Name(span, "even"),
                            [
                                lowered.FuncCall(
                                    span,
                                    lowered.Name(span, "length"),
                                    [lowered.Name(span, "core_funcs")],
                                ),
                            ],
                        ),
                        identity_func,
                        lowered.Function(
                            span,
                            [lowered.Name(span, "a")],
                            lowered.NativeOperation(
                                span,
                                lowered.OperationTypes.MUL,
                                lowered.Scalar(span, 2),
                                lowered.Name(span, "a"),
                            ),
                        ),
                    ),
                ],
            ),
            2,
            0,
        ),
    ),
)
def test_finder(tree, expected_length, expected_defined_length):
    finder = inline_expander._Finder()
    finder.run(tree)
    assert expected_length == len(finder.funcs)
    assert expected_defined_length == len(finder.defined_funcs)


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "tree,inlined,expected",
    (
        (collatz_func, {}, collatz_func),
        (collatz_func, {"nonexistent_name": lowered.Scalar(span, 54)}, collatz_func),
        (collatz_func, {"n": lowered.Scalar(span, 44)}, collatz_func),
        (
            collatz_func.body,
            {"n": lowered.Scalar(span, 44)},
            lowered.Cond(
                span,
                lowered.NativeOperation(
                    span,
                    lowered.OperationTypes.EQUAL,
                    lowered.NativeOperation(
                        span,
                        lowered.OperationTypes.MOD,
                        lowered.Scalar(span, 44),
                        lowered.Scalar(span, 2),
                    ),
                    lowered.Scalar(span, 2),
                ),
                lowered.NativeOperation(
                    span,
                    lowered.OperationTypes.DIV,
                    lowered.Scalar(span, 44),
                    lowered.Scalar(span, 2),
                ),
                lowered.NativeOperation(
                    span,
                    lowered.OperationTypes.ADD,
                    lowered.NativeOperation(
                        span,
                        lowered.OperationTypes.MUL,
                        lowered.Scalar(span, 3),
                        lowered.Scalar(span, 44),
                    ),
                    lowered.Scalar(span, 1),
                ),
            ),
        ),
    ),
)
def test_replacer(tree, inlined, expected):
    inlined_scope = scope.Scope.from_dict(inlined)
    replacer = inline_expander._Replacer(inlined_scope)
    actual = replacer.run(tree)
    assert expected == actual

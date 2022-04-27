# pylint: disable=C0116
from typing import Collection

from pytest import mark

from context import lowered, inline_expander, scope, visitor


class NameFinder(visitor.LoweredASTVisitor[bool]):
    def __init__(self, *names: str) -> None:
        self.names: Collection[str] = names

    def visit_apply(self, node: lowered.Apply) -> bool:
        return node.func.visit(self) or any(map(self.run, node.args))

    def visit_block(self, node: lowered.Block) -> bool:
        return any(map(self.run, node.body))

    def visit_cond(self, node: lowered.Cond) -> bool:
        return node.pred.visit(self) or node.cons.visit(self) or node.else_.visit(self)

    def visit_define(self, node: lowered.Define) -> bool:
        return (node.target.value in self.names) or node.value.visit(self)

    def visit_function(self, node: lowered.Function) -> bool:
        self_names = set(self.names)
        params = {param.value for param in node.params}
        original_names = self.names
        self.names = self_names - params
        result = node.body.visit(self)
        self.names = original_names
        return result

    def visit_list(self, node: lowered.List) -> bool:
        return any(map(self.run, node.elements))

    def visit_pair(self, node: lowered.Pair) -> bool:
        return node.first.visit(self) or node.second.visit(self)

    def visit_name(self, node: lowered.Name) -> bool:
        return node.value in self.names

    def visit_native_op(self, node: lowered.NativeOp) -> bool:
        in_right = False if node.right is None else node.right.visit(self)
        return node.left.visit(self) or in_right

    def visit_scalar(self, node: lowered.Scalar) -> bool:
        return False

    def visit_unit(self, node: lowered.Unit) -> bool:
        return False


collatz_func = lowered.Function(
    lowered.Name("n"),
    lowered.Cond(
        lowered.NativeOp(
            lowered.OperationTypes.EQUAL,
            lowered.NativeOp(
                lowered.OperationTypes.MOD,
                lowered.Name("n"),
                lowered.Scalar(2),
            ),
            lowered.Scalar(0),
        ),
        lowered.NativeOp(
            lowered.OperationTypes.DIV,
            lowered.Name("n"),
            lowered.Scalar(2),
        ),
        lowered.NativeOp(
            lowered.OperationTypes.ADD,
            lowered.NativeOp(
                lowered.OperationTypes.MUL,
                lowered.Scalar(3),
                lowered.Name("n"),
            ),
            lowered.Scalar(1),
        ),
    ),
)
identity_func = lowered.Function(lowered.Name("x"), lowered.Name("x"))


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "funcs,defined,threshold,expected",
    (
        ([], (), 0, []),
        ([], (), 100, []),
        ([identity_func], [identity_func], 0, [identity_func]),
    ),
)
def test_generate_targets(funcs, defined, threshold, expected):
    actual = inline_expander.generate_targets(funcs, defined, threshold)
    assert expected == actual


@mark.inline_expansion
@mark.optimisation
def test_inline_function():
    expected = lowered.Scalar(1)
    name_finder = NameFinder(identity_func.param)
    actual = inline_expander.inline_function(identity_func, lowered.Scalar(1))
    assert not name_finder.run(actual)
    assert expected == actual


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "tree,expected",
    (
        (lowered.Scalar(1.25), 0),
        (lowered.Name("map"), 0),
        (identity_func, 7),
        (collatz_func, 18),
        (
            lowered.Block(
                [
                    lowered.Define(
                        lowered.Name("x"),
                        lowered.Scalar(24),
                    ),
                    lowered.Define(
                        lowered.Name("y"),
                        lowered.NativeOp(
                            lowered.OperationTypes.EXP,
                            lowered.Name("x"),
                            lowered.Scalar(2),
                        ),
                    ),
                    lowered.NativeOp(
                        lowered.OperationTypes.DIV,
                        lowered.Name("x"),
                        lowered.Name("y"),
                    ),
                ],
            ),
            15,
        ),
        (
            lowered.Define(
                lowered.Name("collatz"),
                lowered.Function(
                    lowered.Name("n"),
                    lowered.Cond(
                        lowered.NativeOp(
                            lowered.OperationTypes.EQUAL,
                            lowered.NativeOp(
                                lowered.OperationTypes.MOD,
                                lowered.Name("n"),
                                lowered.Scalar(2),
                            ),
                            lowered.Scalar(0),
                        ),
                        lowered.NativeOp(
                            lowered.OperationTypes.DIV,
                            lowered.Name("n"),
                            lowered.Scalar(2),
                        ),
                        lowered.NativeOp(
                            lowered.OperationTypes.ADD,
                            lowered.NativeOp(
                                lowered.OperationTypes.MUL,
                                lowered.Scalar(3),
                                lowered.Name("n"),
                            ),
                            lowered.Scalar(1),
                        ),
                    ),
                ),
            ),
            22,
        ),
    ),
)
def test_scorer(tree, expected):
    scorer = inline_expander.Scorer()
    actual = scorer.run(tree)
    assert expected == actual


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "tree,expected_length,expected_defined_length",
    (
        (lowered.Unit(), 0, 0),
        (
            lowered.Block([lowered.Define(lowered.Name("id"), identity_func)]),
            1,
            1,
        ),
        (
            lowered.Block(
                [
                    lowered.Cond(
                        lowered.Apply(
                            lowered.Name("even"),
                            lowered.Apply(
                                lowered.Name("length"),
                                lowered.Name("core_funcs"),
                            ),
                        ),
                        identity_func,
                        lowered.Function(
                            lowered.Name("a"),
                            lowered.NativeOp(
                                lowered.OperationTypes.MUL,
                                lowered.Scalar(2),
                                lowered.Name("a"),
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
    finder = inline_expander.Finder()
    finder.run(tree)
    assert expected_length == len(finder.funcs)
    assert expected_defined_length == len(finder.defined_funcs)


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "tree,name,value, expected",
    (
        (collatz_func, "nonexistent_name", lowered.Scalar(54), collatz_func),
        (collatz_func, "n", lowered.Scalar(44), collatz_func),
        (
            collatz_func.body,
            "n",
            lowered.Scalar(44),
            lowered.Cond(
                lowered.NativeOp(
                    lowered.OperationTypes.EQUAL,
                    lowered.NativeOp(
                        lowered.OperationTypes.MOD,
                        lowered.Scalar(44),
                        lowered.Scalar(2),
                    ),
                    lowered.Scalar(0),
                ),
                lowered.NativeOp(
                    lowered.OperationTypes.DIV,
                    lowered.Scalar(44),
                    lowered.Scalar(2),
                ),
                lowered.NativeOp(
                    lowered.OperationTypes.ADD,
                    lowered.NativeOp(
                        lowered.OperationTypes.MUL,
                        lowered.Scalar(3),
                        lowered.Scalar(44),
                    ),
                    lowered.Scalar(1),
                ),
            ),
        ),
    ),
)
def test_replacer(tree, name, value, expected):
    replacer = inline_expander._Replacer(lowered.Name(name), value)
    actual = replacer.run(tree)
    assert expected == actual


@mark.inline_expansion
@mark.optimisation
@mark.parametrize(
    "tree,targets,expected",
    (
        (collatz_func, [], collatz_func),
        (identity_func, [identity_func], identity_func),
        (
            lowered.Function(
                lowered.Name("n"),
                lowered.Cond(
                    lowered.NativeOp(
                        lowered.OperationTypes.EQUAL,
                        lowered.NativeOp(
                            lowered.OperationTypes.MOD,
                            lowered.Name("n"),
                            lowered.Scalar(2),
                        ),
                        lowered.Scalar(0),
                    ),
                    lowered.Apply(
                        identity_func,
                        lowered.NativeOp(
                            lowered.OperationTypes.DIV,
                            lowered.Name("n"),
                            lowered.Scalar(2),
                        ),
                    ),
                    lowered.Apply(
                        identity_func,
                        lowered.NativeOp(
                            lowered.OperationTypes.ADD,
                            lowered.NativeOp(
                                lowered.OperationTypes.MUL,
                                lowered.Scalar(3),
                                lowered.Name("n"),
                            ),
                            lowered.Scalar(1),
                        ),
                    ),
                ),
            ),
            [identity_func],
            lowered.Function(
                lowered.Name("n"),
                lowered.Cond(
                    lowered.NativeOp(
                        lowered.OperationTypes.EQUAL,
                        lowered.NativeOp(
                            lowered.OperationTypes.MOD,
                            lowered.Name("n"),
                            lowered.Scalar(2),
                        ),
                        lowered.Scalar(0),
                    ),
                    lowered.NativeOp(
                        lowered.OperationTypes.DIV,
                        lowered.Name("n"),
                        lowered.Scalar(2),
                    ),
                    lowered.NativeOp(
                        lowered.OperationTypes.ADD,
                        lowered.NativeOp(
                            lowered.OperationTypes.MUL,
                            lowered.Scalar(3),
                            lowered.Name("n"),
                        ),
                        lowered.Scalar(1),
                    ),
                ),
            ),
        ),
        (
            lowered.Block(
                [
                    lowered.Define(lowered.Name("identity"), identity_func),
                    lowered.Function(
                        lowered.Name("n"),
                        lowered.Cond(
                            lowered.NativeOp(
                                lowered.OperationTypes.EQUAL,
                                lowered.NativeOp(
                                    lowered.OperationTypes.MOD,
                                    lowered.Name("n"),
                                    lowered.Scalar(2),
                                ),
                                lowered.Scalar(0),
                            ),
                            lowered.Apply(
                                lowered.Name("identity"),
                                lowered.NativeOp(
                                    lowered.OperationTypes.DIV,
                                    lowered.Name("n"),
                                    lowered.Scalar(2),
                                ),
                            ),
                            lowered.Apply(
                                lowered.Name("identity"),
                                lowered.NativeOp(
                                    lowered.OperationTypes.ADD,
                                    lowered.NativeOp(
                                        lowered.OperationTypes.MUL,
                                        lowered.Scalar(3),
                                        lowered.Name("n"),
                                    ),
                                    lowered.Scalar(1),
                                ),
                            ),
                        ),
                    ),
                ],
            ),
            [identity_func],
            lowered.Block(
                [
                    lowered.Define(lowered.Name("identity"), identity_func),
                    lowered.Function(
                        lowered.Name("n"),
                        lowered.Cond(
                            lowered.NativeOp(
                                lowered.OperationTypes.EQUAL,
                                lowered.NativeOp(
                                    lowered.OperationTypes.MOD,
                                    lowered.Name("n"),
                                    lowered.Scalar(2),
                                ),
                                lowered.Scalar(0),
                            ),
                            lowered.NativeOp(
                                lowered.OperationTypes.DIV,
                                lowered.Name("n"),
                                lowered.Scalar(2),
                            ),
                            lowered.NativeOp(
                                lowered.OperationTypes.ADD,
                                lowered.NativeOp(
                                    lowered.OperationTypes.MUL,
                                    lowered.Scalar(3),
                                    lowered.Name("n"),
                                ),
                                lowered.Scalar(1),
                            ),
                        ),
                    ),
                ],
            ),
        ),
    ),
)
def test_inliner(tree, targets, expected):
    inliner = inline_expander.Inliner(targets)
    actual = inliner.run(tree)
    assert expected == actual

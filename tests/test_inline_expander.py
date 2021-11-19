# pylint: disable=C0116
from pytest import mark

from context import lowered, inline_expander

span = (0, 0)

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
                    )
                )
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
                ]
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

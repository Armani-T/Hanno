from pytest import mark

from context import constant_folder, lowered


@mark.constant_folding
@mark.optimisation
@mark.parametrize(
    "tree,expected",
    (
        (lowered.Unit(), lowered.Unit()),
        (
            lowered.NativeOp(
                lowered.OperationTypes.SUB, lowered.Scalar(7), lowered.Scalar(3)
            ),
            lowered.Scalar(7 - 3),
        ),
        (
            lowered.NativeOp(
                lowered.OperationTypes.ADD,
                lowered.NativeOp(
                    lowered.OperationTypes.MUL,
                    lowered.Scalar(14),
                    lowered.Scalar(2),
                ),
                lowered.Scalar(3),
            ),
            lowered.Scalar(14 * 2 + 3),
        ),
        (
            lowered.Block(
                [
                    lowered.Define(lowered.Name("pi"), lowered.Scalar(3.142)),
                    lowered.Define(lowered.Name("diameter"), lowered.Scalar(14)),
                    lowered.NativeOp(
                        lowered.OperationTypes.MUL,
                        lowered.Name("pi"),
                        lowered.NativeOp(
                            lowered.OperationTypes.EXP,
                            lowered.NativeOp(
                                lowered.OperationTypes.DIV,
                                lowered.Name("diameter"),
                                lowered.Scalar(2),
                            ),
                            lowered.Scalar(2),
                        ),
                    ),
                ],
            ),
            lowered.Scalar(3.142 * ((14 // 2) ** 2)),
        ),
        (
            lowered.Block(
                [
                    lowered.Define(
                        lowered.Name("v"),
                        lowered.NativeOp(lowered.OperationTypes.NEG, lowered.Name("u")),
                    ),
                    lowered.Define(lowered.Name("focus"), lowered.Scalar(53)),
                    lowered.Cond(
                        lowered.NativeOp(
                            lowered.OperationTypes.LESS,
                            lowered.Name("focus"),
                            lowered.Scalar(50),
                        ),
                        lowered.NativeOp(
                            lowered.OperationTypes.ADD,
                            lowered.Name("focus"),
                            lowered.NativeOp(
                                lowered.OperationTypes.DIV,
                                lowered.Name("focus"),
                                lowered.Scalar(2),
                            ),
                        ),
                        lowered.NativeOp(
                            lowered.OperationTypes.SUB,
                            lowered.Name("focus"),
                            lowered.NativeOp(
                                lowered.OperationTypes.DIV,
                                lowered.Name("focus"),
                                lowered.Scalar(2),
                            ),
                        ),
                    ),
                ],
            ),
            lowered.Block(
                [
                    lowered.Define(
                        lowered.Name("v"),
                        lowered.NativeOp(lowered.OperationTypes.NEG, lowered.Name("u")),
                    ),
                    lowered.Scalar(53 - (53 // 2)),
                ],
            ),
        ),
        (
            lowered.Block(
                [
                    lowered.Define(lowered.Name("a"), lowered.Scalar(100)),
                    lowered.Define(lowered.Name("b"), lowered.Name("a")),
                    lowered.NativeOp(
                        lowered.OperationTypes.DIV,
                        lowered.Name("b"),
                        lowered.Scalar(2),
                    ),
                ],
            ),
            lowered.Scalar(100 // 2),
        ),
        (
            lowered.Function(
                lowered.Name("x"),
                lowered.Cond(
                    lowered.Name("x"),
                    lowered.Apply(lowered.Name("f"), lowered.Name("x")),
                    lowered.Apply(lowered.Name("g"), lowered.Name("x")),
                ),
            ),
            lowered.Function(
                lowered.Name("x"),
                lowered.Cond(
                    lowered.Name("x"),
                    lowered.Apply(lowered.Name("f"), lowered.Name("x")),
                    lowered.Apply(lowered.Name("g"), lowered.Name("x")),
                ),
            ),
        ),
        (
            lowered.List(
                [
                    lowered.Pair(
                        lowered.Scalar(1),
                        lowered.NativeOp(
                            lowered.OperationTypes.NEG, lowered.Scalar(24), None
                        ),
                    ),
                ]
            ),
            lowered.List([lowered.Pair(lowered.Scalar(1), lowered.Scalar(-24))]),
        ),
    ),
)
def test_fold_constants(tree, expected):
    actual = constant_folder.fold_constants(tree)
    assert expected == actual


@mark.constant_folding
@mark.optimisation
@mark.parametrize(
    "op,left,right,expected",
    (
        (
            lowered.OperationTypes.EQUAL,
            lowered.Scalar(","),
            lowered.Scalar("."),
            (True, False),
        ),
        (
            lowered.OperationTypes.GREATER,
            lowered.Scalar(164),
            lowered.Scalar(13),
            (True, True),
        ),
        (
            lowered.OperationTypes.JOIN,
            lowered.Scalar(3.1412),
            lowered.Scalar(2.72),
            (False, False),
        ),
        (
            lowered.OperationTypes.LESS,
            lowered.Scalar(149),
            lowered.Scalar(149),
            (True, False),
        ),
        (
            lowered.OperationTypes.ADD,
            lowered.Scalar(14),
            lowered.Scalar(19),
            (False, False),
        ),
    ),
)
def test_fold_comparison(op, left, right, expected):
    actual = constant_folder.fold_comparison(op, left, right)
    assert expected == actual

# pylint: disable=C0116
from pytest import mark

from context import constant_folder, lowered


@mark.constant_folding
@mark.optimisation
@mark.parametrize(
    "source_tree,expected",
    (
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
    ),
)
def test_fold_constants(source_tree, expected):
    actual = constant_folder.fold_constants(source_tree)
    assert expected == actual

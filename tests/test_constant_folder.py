from pytest import mark

from context import constant_folder, lowered

span = (0, 0)


@mark.constant_folding
@mark.optimisation
@mark.parametrize(
    "source,expected",
    (
        (
            lowered.NativeOperation(
                span,
                lowered.OperationTypes.SUB,
                lowered.Scalar(span, 7),
                lowered.Scalar(span, 3),
            ),
            lowered.Scalar(span, 7 - 3),
        ),
        (
            lowered.NativeOperation(
                span,
                lowered.OperationTypes.ADD,
                lowered.NativeOperation(
                    span,
                    lowered.OperationTypes.MUL,
                    lowered.Scalar(span, 14),
                    lowered.Scalar(span, 2),
                ),
                lowered.Scalar(span, 3),
            ),
            lowered.Scalar(span, 14 * 2 + 3),
        ),
        (
            lowered.Block(
                span,
                (
                    lowered.Define(
                        span, lowered.Name(span, "x"), lowered.Scalar(span, 12)
                    ),
                    lowered.NativeOperation(
                        span,
                        lowered.OperationTypes.DIV,
                        lowered.Scalar(span, 1),
                        lowered.NativeOperation(
                            span,
                            lowered.OperationTypes.EXP,
                            lowered.Name(span, "x"),
                            lowered.Scalar(span, 2),
                        ),
                    ),
                ),
            ),
            lowered.Block(
                span,
                [
                    lowered.Vector.unit(span),
                    lowered.Scalar(span, 1 // (12 ** 2)),
                ],
            ),
        ),
        (
            lowered.Block(
                span,
                [
                    lowered.Define(
                        span,
                        lowered.Name(span, "v"),
                        lowered.NativeOperation(
                            span, lowered.OperationTypes.NEG, lowered.Name(span, "u")
                        ),
                    ),
                    lowered.Define(
                        span,
                        lowered.Name(span, "focus"),
                        lowered.Scalar(span, 53),
                    ),
                    lowered.Cond(
                        span,
                        lowered.NativeOperation(
                            span,
                            lowered.OperationTypes.LESS,
                            lowered.Name(span, "focus"),
                            lowered.Scalar(span, 50),
                        ),
                        lowered.NativeOperation(
                            span,
                            lowered.OperationTypes.ADD,
                            lowered.Name(span, "focus"),
                            lowered.NativeOperation(
                                span,
                                lowered.OperationTypes.DIV,
                                lowered.Name(span, "focus"),
                                lowered.Scalar(span, 2),
                            ),
                        ),
                        lowered.NativeOperation(
                            span,
                            lowered.OperationTypes.SUB,
                            lowered.Name(span, "focus"),
                            lowered.NativeOperation(
                                span,
                                lowered.OperationTypes.DIV,
                                lowered.Name(span, "focus"),
                                lowered.Scalar(span, 2),
                            ),
                        ),
                    ),
                ],
            ),
            lowered.Block(
                span,
                [
                    lowered.Define(
                        span,
                        lowered.Name(span, "v"),
                        lowered.NativeOperation(
                            span, lowered.OperationTypes.NEG, lowered.Name(span, "u")
                        ),
                    ),
                    lowered.Vector.unit(span),
                    lowered.Cond(
                        span,
                        lowered.Scalar(span, False),
                        lowered.Scalar(span, 53 + (53 // 2)),
                        lowered.Scalar(span, 53 - (53 // 2)),
                    ),
                ],
            ),
        ),
        (
            lowered.Block(
                span,
                [
                    lowered.Define(
                        span, lowered.Name(span, "a"), lowered.Scalar(span, 100)
                    ),
                    lowered.Define(
                        span, lowered.Name(span, "b"), lowered.Name(span, "a")
                    ),
                    lowered.NativeOperation(
                        span,
                        lowered.OperationTypes.DIV,
                        lowered.Name(span, "b"),
                        lowered.Scalar(span, 2),
                    ),
                ],
            ),
            lowered.Block(
                span,
                [
                    lowered.Vector.unit(span),
                    lowered.Vector.unit(span),
                    lowered.Scalar(span, 100 // 2),
                ],
            ),
        ),
    ),
)
def test_fold_constants(source, expected):
    actual = constant_folder.fold_constants(source)
    assert expected == actual

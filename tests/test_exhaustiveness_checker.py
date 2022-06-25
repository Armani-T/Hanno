from pytest import fail, mark

from context import base, errors, exhaustiveness_checker, typed, types

span = (0, 0)
type_ = types.TypeVar.unknown(span)


@mark.exhaustiveness_checking
@mark.parametrize(
    "tree",
    (
        type_,
        typed.Define(span, type_, base.UnitPattern(span), typed.Unit(span)),
        typed.Match(
            span,
            type_,
            typed.List(
                span, type_, [typed.Scalar(span, type_, "It's only me here...")]
            ),
            [
                (
                    base.ListPattern(span, [], None),
                    typed.Pair(
                        span,
                        type_,
                        typed.Scalar(span, type_, 0),
                        typed.Scalar(span, type_, 0),
                    ),
                ),
                (
                    base.FreeName(span, "_"),
                    typed.Pair(
                        span,
                        type_,
                        typed.Scalar(span, type_, -1),
                        typed.Scalar(span, type_, -1),
                    ),
                ),
            ],
        ),
        typed.Apply(
            span,
            type_,
            typed.Name(span, type_, "plus_one"),
            typed.Scalar(span, type_, 11),
        ),
        typed.Match(
            span,
            type_,
            typed.Name(span, type_, "grade"),
            [
                (
                    base.ScalarPattern(span, "A"),
                    typed.Scalar(span, type_, 75),
                ),
                (
                    base.ScalarPattern(span, "B"),
                    typed.Scalar(span, type_, 65),
                ),
                (
                    base.ScalarPattern(span, "C"),
                    typed.Scalar(span, type_, 55),
                ),
                (
                    base.ScalarPattern(span, "D"),
                    typed.Scalar(span, type_, 40),
                ),
                (
                    base.FreeName(span, "_"),
                    typed.Scalar(span, type_, 0),
                ),
            ],
        ),
        typed.Cond(
            span,
            type_,
            typed.Apply(
                span,
                type_,
                typed.Apply(
                    span,
                    type_,
                    typed.Name(span, type_, ">"),
                    typed.Name(span, type_, "x"),
                ),
                typed.Scalar(span, type_, 0),
            ),
            typed.Scalar(span, type_, 1),
            typed.Apply(
                span,
                type_,
                typed.Apply(
                    span,
                    type_,
                    typed.Name(span, type_, "*"),
                    typed.Name(span, type_, "x"),
                ),
                typed.Apply(
                    span,
                    type_,
                    typed.Name(span, type_, "factorial"),
                    typed.Name(span, type_, "x"),
                ),
            ),
        ),
    ),
)
def test_check_exhaustiveness_success(tree):
    assert exhaustiveness_checker.check_exhaustiveness(tree) is None


@mark.exhaustiveness_checking
@mark.parametrize(
    "tree,expected_offender",
    (
        (
            typed.Match(span, type_, typed.Name(span, type_, "seq"), []),
            None,
        ),
        (
            typed.Define(
                span,
                type_,
                base.PairPattern(
                    span,
                    base.FreeName(span, "pi"),
                    base.ScalarPattern(span, 0),
                ),
                typed.Scalar(span, type_, 3.142),
            ),
            base.ScalarPattern(span, 0),
        ),
        (
            typed.Block(
                span,
                type_,
                [
                    typed.Define(
                        span,
                        type_,
                        base.FreeName(span, "x"),
                        typed.Scalar(span, type_, 12),
                    ),
                    typed.Match(
                        span,
                        type_,
                        typed.Name(span, type_, "x"),
                        [
                            (
                                base.ScalarPattern(span, 0),
                                typed.Scalar(span, type_, "Zero"),
                            ),
                            (
                                base.ScalarPattern(span, 1),
                                typed.Scalar(span, type_, "One"),
                            ),
                            (
                                base.ScalarPattern(span, 2),
                                typed.Scalar(span, type_, "Two"),
                            ),
                            (
                                base.ScalarPattern(span, 3),
                                typed.Scalar(span, type_, "Three"),
                            ),
                        ],
                    ),
                ],
            ),
            base.ScalarPattern(span, 3),
        ),
        (
            typed.Function(
                span,
                type_,
                base.FreeName(span, "seq"),
                typed.Match(
                    span,
                    type_,
                    typed.Name(span, type_, "seq"),
                    [
                        (
                            base.ListPattern(
                                span,
                                [base.FreeName(span, "_")],
                                base.FreeName(span, "rest"),
                            ),
                            typed.Apply(
                                span,
                                type_,
                                typed.Apply(
                                    span,
                                    type_,
                                    typed.Name(span, type_, "+"),
                                    typed.Scalar(span, type_, 1),
                                ),
                                typed.Apply(
                                    span,
                                    type_,
                                    typed.Name(span, type_, "len"),
                                    typed.Name(span, type_, "seq"),
                                ),
                            ),
                        )
                    ],
                ),
            ),
            base.ListPattern(
                span,
                [base.FreeName(span, "_")],
                base.FreeName(span, "rest"),
            ),
        ),
        (
            typed.Function(
                span,
                type_,
                base.ListPattern(span, [], None),
                typed.Scalar(span, type_, True),
            ),
            base.ListPattern(span, [], None),
        ),
    ),
)
def test_check_exhaustiveness_failure(tree, expected_offender):
    try:
        checker = exhaustiveness_checker.ExhaustivenessChecker()
        checker.run(tree)
    except errors.RefutablePatternError as error:
        assert error.pattern == expected_offender
    else:
        fail("A `RefutablePatternError` was not raised!")

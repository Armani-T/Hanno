from os.path import sep
from pytest import mark

from context import base, string_expander, types

span = (0, 0)


@mark.parametrize(
    "source,expected",
    (
        ("\\f", "\f"),
        ("\\5F", "_"),
        ("\\u005F", "_"),
        ("\\U00005f", "_"),
        ("\\u039B", "Λ"),
        ("\\U0003c2", "ς"),
        ("\\U01F4A9", "💩"),
    ),
)
def test_expand_string(source, expected):
    actual = string_expander.expand_string(source)
    assert expected == actual


@mark.parametrize(
    "tree,expected",
    (
        (base.Unit(span), base.Unit(span)),
        (types.TypeName(span, "Int"), types.TypeName(span, "Int")),
        (base.Scalar(span, "abcdef"), base.Scalar(span, "abcdef")),
        (
            base.Scalar(span, "\\U01F4A9"),
            base.Scalar(span, "💩"),
        ),
        (
            base.Block(
                span,
                [
                    base.Annotation(
                        span, base.Name(span, "pi"), types.TypeName(span, "Int")
                    ),
                    base.Cond(
                        span,
                        base.Scalar(span, False),
                        base.Scalar(span, "This is definitely not a path!"),
                        base.Apply(
                            span,
                            base.Apply(
                                span, base.Name(span, "+"), base.Scalar(span, "C:")
                            ),
                            base.Scalar(span, "\\/Users"),
                        ),
                    ),
                ],
            ),
            base.Block(
                span,
                [
                    base.Annotation(
                        span, base.Name(span, "pi"), types.TypeName(span, "Int")
                    ),
                    base.Cond(
                        span,
                        base.Scalar(span, False),
                        base.Scalar(span, "This is definitely not a path!"),
                        base.Apply(
                            span,
                            base.Apply(
                                span, base.Name(span, "+"), base.Scalar(span, "C:")
                            ),
                            base.Scalar(span, f"{sep}Users"),
                        ),
                    ),
                ],
            ),
        ),
        (
            base.Define(
                span,
                base.FreeName(span, "pprint_func"),
                base.Function(
                    span,
                    base.PairPattern(
                        span, base.FreeName(span, "param"), base.FreeName(span, "body")
                    ),
                    base.Apply(
                        span,
                        base.Scalar(span, "\\u03bb"),
                        base.Apply(
                            span,
                            base.Apply(
                                span,
                                base.Name(span, "show"),
                                base.Name(span, "param"),
                            ),
                            base.Apply(
                                span,
                                base.Scalar(span, "\\u2022"),
                                base.Apply(
                                    span,
                                    base.Name(span, "show"),
                                    base.Name(span, "body"),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            base.Define(
                span,
                base.FreeName(span, "pprint_func"),
                base.Function(
                    span,
                    base.PairPattern(
                        span, base.FreeName(span, "param"), base.FreeName(span, "body")
                    ),
                    base.Apply(
                        span,
                        base.Scalar(span, "λ"),
                        base.Apply(
                            span,
                            base.Apply(
                                span,
                                base.Name(span, "show"),
                                base.Name(span, "param"),
                            ),
                            base.Apply(
                                span,
                                base.Scalar(span, "•"),
                                base.Apply(
                                    span,
                                    base.Name(span, "show"),
                                    base.Name(span, "body"),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            base.List(
                span,
                (
                    base.Pair(
                        span,
                        base.Scalar(span, "\\U000410"),
                        base.Scalar(span, "\\u0430"),
                    ),
                    base.Pair(
                        span,
                        base.Scalar(span, "\\U000411"),
                        base.Scalar(span, "\\u0431"),
                    ),
                    base.Pair(
                        span,
                        base.Scalar(span, "\\U000412"),
                        base.Scalar(span, "\\u0432"),
                    ),
                    base.Pair(
                        span,
                        base.Scalar(span, "\\U000413"),
                        base.Scalar(span, "\\u0433"),
                    ),
                    base.Pair(
                        span,
                        base.Scalar(span, "\\U000414"),
                        base.Scalar(span, "\\u0434"),
                    ),
                ),
            ),
            base.List(
                span,
                (
                    base.Pair(span, base.Scalar(span, "А"), base.Scalar(span, "а")),
                    base.Pair(span, base.Scalar(span, "Б"), base.Scalar(span, "б")),
                    base.Pair(span, base.Scalar(span, "В"), base.Scalar(span, "в")),
                    base.Pair(span, base.Scalar(span, "Г"), base.Scalar(span, "г")),
                    base.Pair(span, base.Scalar(span, "Д"), base.Scalar(span, "д")),
                ),
            ),
        ),
        (
            base.Match(
                span,
                base.Name(span, "seq"),
                (
                    (base.ListPattern(span, [], None), base.Scalar(span, "empty")),
                    (
                        base.ListPattern(
                            span,
                            [base.ScalarPattern(span, "first")],
                            base.FreeName(span, "rest"),
                        ),
                        base.Scalar(span, "full"),
                    ),
                ),
            ),
            base.Match(
                span,
                base.Name(span, "seq"),
                (
                    (base.ListPattern(span, [], None), base.Scalar(span, "empty")),
                    (
                        base.ListPattern(
                            span,
                            [base.ScalarPattern(span, "first")],
                            base.FreeName(span, "rest"),
                        ),
                        base.Scalar(span, "full"),
                    ),
                ),
            ),
        ),
    ),
)
def test_expand_strings(tree, expected):
    actual = string_expander.expand_strings(tree)
    assert expected == actual

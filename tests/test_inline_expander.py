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

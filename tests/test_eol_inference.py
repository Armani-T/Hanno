# pylint: disable=C0116
from pytest import mark

from context import lex


@mark.eol_inference
@mark.parametrize(
    "stream,expected",
    (
        ((), ()),
        (
            (lex.Token((0, 3), lex.TokenTypes.float_, "1.01"),),
            (
                lex.Token((0, 3), lex.TokenTypes.float_, "1.01"),
                lex.Token((3, 4), lex.TokenTypes.eol, None),
            ),
        ),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.integer, "1"),
                lex.Token((1, 2), lex.TokenTypes.diamond, None),
                lex.Token((2, 3), lex.TokenTypes.integer, "1"),
            ),
            (
                lex.Token((0, 1), lex.TokenTypes.integer, "1"),
                lex.Token((1, 2), lex.TokenTypes.diamond, None),
                lex.Token((2, 3), lex.TokenTypes.integer, "1"),
                lex.Token((3, 4), lex.TokenTypes.eol, None),
            ),
        ),
        (
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((1, 2), lex.TokenTypes.rbracket, None),
            ),
            (
                lex.Token((0, 1), lex.TokenTypes.lbracket, None),
                lex.Token((1, 2), lex.TokenTypes.rbracket, None),
                lex.Token((2, 3), lex.TokenTypes.eol, None),
            ),
        ),
    ),
)
def test_infer_eols(stream, expected):
    actual = tuple(lex.infer_eols(lex.TokenStream(stream, [lex.TokenTypes.comment])))
    expected = tuple(expected)
    assert expected == actual


@mark.eol_inference
@mark.parametrize(
    "prev,current,next_",
    (
        (
            lex.Token((0, 3), lex.TokenTypes.integer, "100"),
            lex.Token((3, 6), lex.TokenTypes.whitespace, " \n "),
            lex.Token((6, 9), lex.TokenTypes.integer, "100"),
        ),
        (
            lex.Token((86, 87), lex.TokenTypes.rparen, None),
            lex.Token((3, 6), lex.TokenTypes.whitespace, "\n\n\n\n"),
            lex.Token((88, 89), lex.TokenTypes.let, None),
        ),
        (
            lex.Token((14, 15), lex.TokenTypes.true, None),
            lex.Token((3, 6), lex.TokenTypes.whitespace, "\n    "),
            lex.Token((12, 13), lex.TokenTypes.lparen, None),
        ),
    ),
)
def test_can_add_eol_for_true_cases(prev, current, next_):
    assert lex.can_add_eol(prev, current, next_, 0)


@mark.eol_inference
@mark.parametrize(
    "prev,current,next_,paren_stack_size",
    (
        (
            lex.Token((0, 1), lex.TokenTypes.diamond, None),
            lex.Token((1, 2), lex.TokenTypes.whitespace, "\t"),
            lex.Token((2, 3), lex.TokenTypes.integer, "100"),
            0,
        ),
        (
            lex.Token((0, 1), lex.TokenTypes.diamond, None),
            lex.Token((1, 3), lex.TokenTypes.whitespace, "  "),
            lex.Token((3, 6), lex.TokenTypes.integer, "100"),
            2,
        ),
        (
            lex.Token((241, 242), lex.TokenTypes.name_, "f_100"),
            lex.Token((242, 243), lex.TokenTypes.whitespace, " "),
            lex.Token((243, 244), lex.TokenTypes.integer, "100"),
            1,
        ),
    ),
)
def test_can_add_eol_for_false_cases(prev, current, next_, paren_stack_size):
    assert not lex.can_add_eol(prev, current, next_, paren_stack_size)

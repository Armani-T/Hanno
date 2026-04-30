from pytest import mark

from context import ast_sorter, lex, parse

prepare = lambda source: parse.parse(lex.infer_eols(lex.lex(source)))
span = (0, 0)


@mark.optimisation
@mark.parametrize(
    "source,expected_source",
    (
        ("[1, 2, 3, 4, 5]", "[1, 2, 3, 4, 5]"),
        (
            "let z = [y, y, y]\nlet y = x + 1\nlet x = 12",
            "let x = 12\nlet y = x + 1\nlet z = [y, y, y]",
        ),
        (
            "let z = id (double 12)\nlet id = \\x -> x\nlet double = \\x -> (x, x)",
            "let double = \\x -> (x, x)\nlet id = \\x -> x\nlet z = id (double 12)",
        ),
        (
            (
                "let d = a <> b <> c\nlet b = []\nlet c = [i * 2, i * 3, i * 4]\n"
                'let a = [i / 3, i / 2, i]\nlet i = 10\nmatch d | [] -> "Nothing" '
                '| ^e -> "Series from e" | _ -> "Series for i"'
            ),
            (
                "let i = 10\nlet b = []\nlet a = [i / 3, i / 2, i]\n"
                "let c = [i * 2, i * 3, i * 4]\nlet d = a <> b <> c\nmatch d | [] -> "
                '"Nothing" | ^e -> "Series from e" | _ -> "Series for i"'
            ),
        ),
    ),
)
def test_topological_sort(source, expected_source):
    actual = ast_sorter.topological_sort(prepare(source))
    expected = prepare(expected_source)
    assert expected == actual

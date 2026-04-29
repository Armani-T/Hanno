from pytest import mark

from context import codegen, lex, parse, pprint, type_inference, types

span = (0, 0)

_prepare = lambda source: parse.parse(lex.infer_eols(lex.lex(source)))


@mark.error_handling
def test_show_type_var_with_name():
    type_var = types.TypeVar((0, 0), "t")
    assert pprint.show_type_var(type_var) == "t"
    assert pprint.show_type_var(type_var) not in tuple(pprint.var_names.values())


@mark.error_handling
def test_show_type_var_with_int_name():
    type_var = types.TypeVar.unknown((0, 0))
    pprint.var_names[type_var.value] = "a"
    assert pprint.show_type_var(type_var) == "a"
    assert pprint.show_type_var(type_var) in tuple(pprint.var_names.values())


@mark.error_handling
def test_show_type_var_unknown():
    type_var = types.TypeVar.unknown((0, 0))
    assert len(pprint.show_type_var(type_var)) == 1
    assert pprint.show_type_var(type_var) not in pprint.available_letters
    assert pprint.show_type_var(type_var) in pprint.USABLE_LETTERS
    assert pprint.show_type_var(type_var) in tuple(pprint.var_names.values())


@mark.error_handling
@mark.parametrize(
    "source,untyped_expected,typed_expected,lowered_expected",
    (
        ("()", "()", "()", "()"),
        (
            "correct :: Int -> Bool\nanswer :: Int\nif correct(answer) then True else False",
            "\ncorrect :: Int -> Bool\nanswer :: Int\nif correct answer then True else False",
            "\n()\n()\nif [correct :: Int -> Bool] [answer :: Int] then True else False\n# type: Bool",
            "\n{\n()\n()\ncorrect(answer) ? True : False\n}",
        ),
        (
            "let duplicate = \\x -> (x, x)\nlet (x, []) = duplicate [12]",
            "\nlet duplicate = \\x -> (x, x)\nlet (x, []) = duplicate [12]",
            (
                "\nlet duplicate :: c . c -> c , c = \\x -> ([x :: c], [x :: c])\n"
                "let (x, []) :: List[Int] , List[Int] = [duplicate :: List[Int] -> "
                "List[Int] , List[Int]] [12]\n# type: List[Int] , List[Int]"
            ),
            None,
        ),
        (
            (
                'x :: List[String]\nmatch (["hi", "hello"], ()) | (^x, _) -> "Just a '
                'greeting!" | ([], ()) -> "It\'s nothing" | (["hi", ..rest], _) -> '
                '"Other Greetings" | _ -> "Something else"'
            ),
            (
                "\nx :: List[String]\ncase (['hi', 'hello'], ()) of (^x, _) -> 'Just "
                "a greeting!', ([], ()) -> \"It's nothing\", (['hi', ..rest], _) -> "
                "'Other Greetings', _ -> 'Something else'"
            ),
            (
                "\n()\ncase (['hi', 'hello'], ()) of (^x, _) -> 'Just a greeting!', "
                "([], ()) -> \"It's nothing\", (['hi', ..rest], _) -> 'Other "
                "Greetings', _ -> 'Something else'\n# type: String"
            ),
            None,
        ),
    ),
)
def test_all_ast_printers(source, untyped_expected, typed_expected, lowered_expected):
    untyped_ast = _prepare(source) if isinstance(source, str) else source
    assert untyped_expected == untyped_ast.visit(pprint.ASTPrinter())

    typed_ast = type_inference.infer_types(untyped_ast)
    assert typed_expected == typed_ast.visit(pprint.TypedASTPrinter())

    if lowered_expected is not None:
        lowered_ast = codegen.simplify(typed_ast)
        assert lowered_expected == lowered_ast.visit(pprint.LoweredASTPrinter())

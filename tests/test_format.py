from string import ascii_lowercase

from pytest import mark

from context import codegen, lex, parse, prepare, pprint, type_inference, types

span = (0, 0)


@mark.error_handling
def test_show_type_var_with_name():
    pprint.available_letters = list(ascii_lowercase)
    type_var = types.TypeVar(span, "tv")
    assert pprint.show_type_var(type_var) == "tv"
    assert pprint.show_type_var(type_var) not in tuple(pprint.var_names.values())


@mark.error_handling
def test_show_type_var_unknown():
    pprint.available_letters = list(ascii_lowercase)
    type_var = types.TypeVar.unknown(span)
    assert len(pprint.show_type_var(type_var)) == 1
    assert pprint.show_type_var(type_var) not in pprint.available_letters
    assert pprint.show_type_var(type_var) in ascii_lowercase
    assert pprint.show_type_var(type_var) in tuple(pprint.var_names.values())


@mark.error_handling
def test_show_over_26_type_vars():
    pprint.available_letters = list(ascii_lowercase)
    __ = [
        pprint.show_type_var(types.TypeVar.unknown(span))
        for _ in range(len(ascii_lowercase) + 1)
    ]
    type_var = types.TypeVar.unknown(span)
    assert pprint.show_type_var(type_var) not in pprint.available_letters
    assert pprint.show_type_var(type_var) not in ascii_lowercase


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
                "\nlet duplicate :: a . a -> a , a = \\x -> ([x :: a], [x :: a])\n"
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
    pprint.available_letters = list(ascii_lowercase)

    printer = pprint.ASTPrinter()
    untyped_ast = prepare(source)
    assert untyped_expected == printer.run(untyped_ast)

    if typed_expected is not None:
        printer = pprint.TypedASTPrinter()
        typed_ast = type_inference.infer_types(untyped_ast)
        assert typed_expected == printer.run(typed_ast)

    if lowered_expected is not None:
        printer = pprint.LoweredASTPrinter()
        lowered_ast = codegen.simplify(
            untyped_ast if typed_expected is None else typed_ast
        )
        assert lowered_expected == printer.run(lowered_ast)

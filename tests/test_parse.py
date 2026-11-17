from pytest import mark, raises

from context import base, errors, lex, parse, types

span = (0, 0)

prepare = lambda source: lex.infer_eols(lex.lex(source))


@mark.integration
@mark.parsing
@mark.parametrize(
    "source,expected",
    (
        ("", base.Unit(span)),
        ("False", base.Scalar(span, False)),
        ("(True)", base.Scalar(span, True)),
        ("845.3142", base.Scalar(span, 845.3142)),
        ('"αβγ"', base.Scalar(span, "αβγ")),
        ("()", base.Unit(span)),
        (
            "[1, 2, 3, 4, 5]",
            base.List(
                span,
                (
                    base.Scalar(span, 1),
                    base.Scalar(span, 2),
                    base.Scalar(span, 3),
                    base.Scalar(span, 4),
                    base.Scalar(span, 5),
                ),
            ),
        ),
        (
            'print_line("Hello " + "World")',
            base.Apply(
                span,
                base.Name(span, "print_line"),
                base.Apply(
                    span,
                    base.Apply(span, base.Name(span, "+"), base.Scalar(span, "Hello ")),
                    base.Scalar(span, "World"),
                ),
            ),
        ),
        (
            "21 ^ -2",
            base.Apply(
                span,
                base.Apply(span, base.Name(span, "^"), base.Scalar(span, 21)),
                base.Apply(span, base.Name(span, "~"), base.Scalar(span, 2)),
            ),
        ),
        (
            "let xor(a, b) = (a or b) and not (a and b)",
            base.Define(
                span,
                base.FreeName(span, "xor"),
                base.Function(
                    span,
                    base.PairPattern(
                        span, base.FreeName(span, "a"), base.FreeName(span, "b")
                    ),
                    base.Apply(
                        span,
                        base.Apply(
                            span,
                            base.Name(span, "and"),
                            base.Apply(
                                span,
                                base.Apply(
                                    span, base.Name(span, "or"), base.Name(span, "a")
                                ),
                                base.Name(span, "b"),
                            ),
                        ),
                        base.Apply(
                            span,
                            base.Name(span, "not"),
                            base.Apply(
                                span,
                                base.Apply(
                                    span,
                                    base.Name(span, "and"),
                                    base.Name(span, "a"),
                                ),
                                base.Name(span, "b"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            "\\x, y, z -> x - y - (z + 1)",
            base.Function(
                span,
                base.PairPattern(
                    span,
                    base.FreeName(span, "x"),
                    base.PairPattern(
                        span, base.FreeName(span, "y"), base.FreeName(span, "z")
                    ),
                ),
                base.Apply(
                    span,
                    base.Apply(
                        span,
                        base.Name(span, "-"),
                        base.Apply(
                            span,
                            base.Apply(
                                span, base.Name(span, "-"), base.Name(span, "x")
                            ),
                            base.Name(span, "y"),
                        ),
                    ),
                    base.Apply(
                        span,
                        base.Apply(span, base.Name(span, "+"), base.Name(span, "z")),
                        base.Scalar(span, 1),
                    ),
                ),
            ),
        ),
        (
            '(141, return True, pi, "", ())',
            base.Pair(
                span,
                base.Scalar(span, 141),
                base.Pair(
                    span,
                    base.Apply(
                        span, base.Name(span, "return"), base.Scalar(span, True)
                    ),
                    base.Pair(
                        span,
                        base.Name(span, "pi"),
                        base.Pair(
                            span,
                            base.Scalar(span, ""),
                            base.Unit(span),
                        ),
                    ),
                ),
            ),
        ),
        (
            "let pair = (func_1(1, 2), func_2(3, 4))",
            base.Define(
                span,
                base.FreeName(span, "pair"),
                base.Pair(
                    span,
                    base.Apply(
                        span,
                        base.Name(span, "func_1"),
                        base.Pair(span, base.Scalar(span, 1), base.Scalar(span, 2)),
                    ),
                    base.Apply(
                        span,
                        base.Name(span, "func_2"),
                        base.Pair(span, base.Scalar(span, 3), base.Scalar(span, 4)),
                    ),
                ),
            ),
        ),
        (
            "plus_1 :: Int -> Int",
            base.Annotation(
                span,
                base.Name(span, "plus_1"),
                types.TypeApply.func(
                    span, types.TypeName(span, "Int"), types.TypeName(span, "Int")
                ),
            ),
        ),
        (
            "type Span(line :: Int, col :: Int)\nSpan(4, 88)",
            base.Block(
                span,
                [
                    base.ProductType(
                        span,
                        types.TypeName(span, "Span"),
                        (
                            base.Annotation(
                                span,
                                base.Name(span, "line"),
                                types.TypeName(span, "Int"),
                            ),
                            base.Annotation(
                                span,
                                base.Name(span, "col"),
                                types.TypeName(span, "Int"),
                            ),
                        ),
                    ),
                    base.Apply(
                        span,
                        types.TypeName(span, "Span"),
                        base.Pair(span, base.Scalar(span, 4), base.Scalar(span, 88)),
                    ),
                ],
            ),
        ),
        (
            "type Peano = Zero | Succ(num :: Peano)",
            base.SumType(
                span,
                types.TypeName(span, "Peano"),
                (
                    base.ProductType(span, types.TypeName(span, "Zero"), ()),
                    base.ProductType(
                        span,
                        types.TypeName(span, "Succ"),
                        (
                            base.Annotation(
                                span,
                                base.Name(span, "num"),
                                types.TypeName(span, "Peano"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            "match val | Yes x -> x | No -> 0",
            base.Match(
                span,
                base.Name(span, "val"),
                (
                    (base.ADTPattern(span, types.TypeName(span, "Yes"), base.FreeName(span, "x")), base.Name(span, "x")),
                    (base.ADTPattern(span, types.TypeName(span, "No"), None), base.Scalar(span, 1)),
                ),
            ),
        ),
        (
            'match result | Greater -> ">" | Equal -> "=" | Less -> "<"',
            base.Match(
                span,
                base.Name(span, "result"),
                (
                    (base.ADTPattern(span, types.TypeName(span, "Greater"), None), base.Scalar(span, ">")),
                    (base.ADTPattern(span, types.TypeName(span, "Equal"), None), base.Scalar(span, "=")),
                    (base.ADTPattern(span, types.TypeName(span, "Less"), None), base.Scalar(span, "<")),
                ),
            ),
        ),
        (
            "type Maybe[a] = No | Yes[a](value :: a)",
            base.SumType(
                span,
                types.TypeApply(
                    span, types.TypeName(span, "Maybe"), types.TypeVar(span, "a")
                ),
                (
                    base.ProductType(span, types.TypeName(span, "No"), ()),
                    base.ProductType(
                        span,
                        types.TypeApply(
                            span, types.TypeName(span, "Yes"), types.TypeVar(span, "a")
                        ),
                        (
                            base.Annotation(
                                span, base.Name(span, "value"), types.TypeVar(span, "a")
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
def test_parser(source, expected):
    lexed_source = prepare(source)
    actual = parse.parse(lexed_source)
    assert expected == actual


@mark.integration
@mark.parsing
def test_parse_annotation():
    stream = lex.TokenStream(
        (
            lex.Token(span, lex.TokenTypes.double_colon, None),
            lex.Token(span, lex.TokenTypes.name, "Int"),
        ),
        (),
    )
    with raises(errors.UnexpectedTokenError):
        parse.parse_annotation(stream, base.Scalar(span, 66))

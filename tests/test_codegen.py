from pytest import mark, param

from context import codegen, lex, lowered, parse

TAKE_SOURCE = """
let take (seq, n) :=
    let inner (seq_, n_, cache) = match seq_
        | [] -> cache
        | [x, ..xs] ->
            if n > 0  then inner (xs, n - 1, [x] <> cache) else cache

    inner (seq, n, [])
end
"""

span = (0, 0)

_prepare = lambda source: parse.parse(lex.infer_eols(lex.lex(source)))


@mark.codegen
@mark.parametrize(
    "node,expected",
    (
        (
            lowered.Define(
                lowered.Name("collatz_step"),
                lowered.Cond(
                    lowered.NativeOp(
                        lowered.OperationTypes.EQUAL,
                        lowered.NativeOp(
                            lowered.OperationTypes.MOD,
                            lowered.Name("n"),
                            lowered.Scalar(2),
                        ),
                        lowered.Scalar(0),
                    ),
                    lowered.Function(
                        lowered.Name("x"),
                        lowered.NativeOp(
                            lowered.OperationTypes.ADD,
                            lowered.NativeOp(
                                lowered.OperationTypes.MUL,
                                lowered.Scalar(3),
                                lowered.Name("x"),
                            ),
                            lowered.Scalar(1),
                        ),
                    ),
                    lowered.Function(lowered.Name("x"), lowered.Name("x")),
                ),
            ),
            (
                codegen.Instruction(codegen.OpCodes.LOAD_INT, (0,)),
                codegen.Instruction(codegen.OpCodes.LOAD_INT, (2,)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 0)),
                codegen.Instruction(codegen.OpCodes.NATIVE, (8,)),
                codegen.Instruction(codegen.OpCodes.NATIVE, (3,)),
                codegen.Instruction(codegen.OpCodes.BRANCH, (2,)),
                codegen.Instruction(
                    codegen.OpCodes.LOAD_FUNC,
                    (
                        (
                            codegen.Instruction(codegen.OpCodes.LOAD_INT, (1,)),
                            codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 0)),
                            codegen.Instruction(codegen.OpCodes.LOAD_INT, (3,)),
                            codegen.Instruction(codegen.OpCodes.NATIVE, (9,)),
                            codegen.Instruction(codegen.OpCodes.NATIVE, (1,)),
                        ),
                    ),
                ),
                codegen.Instruction(codegen.OpCodes.JUMP, (1,)),
                codegen.Instruction(
                    codegen.OpCodes.LOAD_FUNC,
                    ((codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 0)),),),
                ),
                codegen.Instruction(codegen.OpCodes.STORE_NAME, (1,)),
            ),
        ),
        (
            lowered.Block(
                [
                    lowered.Define(
                        lowered.Name("file_path"),
                        lowered.NativeOp(
                            lowered.OperationTypes.ADD,
                            lowered.Name("folder_path"),
                            lowered.NativeOp(
                                lowered.OperationTypes.ADD,
                                lowered.Scalar("/"),
                                lowered.Name("file_name"),
                            ),
                        ),
                    ),
                    lowered.Define(
                        lowered.Name("file"),
                        lowered.Apply(
                            lowered.Name("open_file"),
                            lowered.Name("file_path"),
                        ),
                    ),
                    lowered.Define(
                        lowered.Name("file_contents"),
                        lowered.Apply(
                            lowered.Name("read_file"),
                            lowered.Name("file"),
                        ),
                    ),
                    lowered.Define(
                        lowered.Name("exit_code"),
                        lowered.Apply(
                            lowered.Name("close_file"),
                            lowered.Name("file"),
                        ),
                    ),
                    lowered.Apply(
                        lowered.Name("println"),
                        lowered.Name("file_contents"),
                    ),
                    lowered.Pair(
                        lowered.Name("exit_code"), lowered.Name("file_contents")
                    ),
                ],
            ),
            (
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 0)),
                codegen.Instruction(codegen.OpCodes.LOAD_STRING, ("/",)),
                codegen.Instruction(codegen.OpCodes.NATIVE, (1,)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 1)),
                codegen.Instruction(codegen.OpCodes.NATIVE, (1,)),
                codegen.Instruction(codegen.OpCodes.STORE_NAME, (2,)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 2)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 3)),
                codegen.Instruction(codegen.OpCodes.APPLY, ()),
                codegen.Instruction(codegen.OpCodes.STORE_NAME, (4,)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 4)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 5)),
                codegen.Instruction(codegen.OpCodes.APPLY, ()),
                codegen.Instruction(codegen.OpCodes.STORE_NAME, (6,)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 4)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 7)),
                codegen.Instruction(codegen.OpCodes.APPLY, ()),
                codegen.Instruction(codegen.OpCodes.STORE_NAME, (8,)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 6)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 9)),
                codegen.Instruction(codegen.OpCodes.APPLY, ()),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 6)),
                codegen.Instruction(codegen.OpCodes.LOAD_NAME, (1, 8)),
                codegen.Instruction(codegen.OpCodes.BUILD_PAIR, ()),
            ),
        ),
    ),
)
def test_instruction_generator(node, expected):
    generator = codegen.InstructionGenerator()
    actual = tuple(generator.run(node))
    assert expected == actual


@mark.codegen
@mark.parametrize(
    "pool,expected",
    (
        ([], b""),
        (
            (b"\x08\x00\x00\x00\x00\x00\x00\x00",),
            b"\x00\x00\x00\x08\x08\x00\x00\x00\x00\x00\x00\x00",
        ),
        (
            (
                b"Hello, World!",
                b"Test #3",
                b"z" * 301,
            ),
            (
                (
                    b"\x00\x00\x00\x0dHello, World!"
                    b"\x00\x00\x00\x07Test #3"
                    b"\x00\x00\x01\x2d%b"
                )
                % (b"z" * 301)
            ),
        ),
    ),
)
def test_encode_pool(pool, expected):
    actual = codegen.encode_pool(pool)
    assert expected == actual
    for func_body in pool:
        assert func_body in actual


@mark.codegen
@mark.parametrize(
    "kwargs,expected",
    (
        (
            {
                "stream_size": 111,
                "func_pool_size": 18,
                "string_pool_size": 53,
                "encoding_used": "UTF8",
            },
            (
                b"F:\x00\x00\x00\x12S:\x00\x00\x00\x35C:\x00\x00\x00\x6f"
                b"E:utf-8\x00\x00\x00\x00\x00\x00\x00"
            ),
        ),
        (
            {
                "stream_size": 1342,
                "func_pool_size": 84,
                "string_pool_size": 101,
                "encoding_used": "Latin-1",
            },
            (
                b"F:\x00\x00\x00\x54S:\x00\x00\x00\x65C:\x00\x00\x05\x3e"
                b"E:iso8859-1\x00\x00\x00"
            ),
        ),
    ),
)
def test_generate_header(kwargs, expected):
    actual = codegen.generate_header(**kwargs)
    assert expected == actual


@mark.codegen
@mark.parametrize(
    "instruction,expected_code,expected_func_pool,expected_string_pool",
    (
        (
            codegen.Instruction(codegen.OpCodes.LOAD_BOOL, (True,)),
            b"\xff",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.LOAD_INT, (-4200,)),
            b"\xf0\x00\x00\x10\x68",
            [],
            [],
        ),
        param(
            codegen.Instruction(codegen.OpCodes.LOAD_FLOAT, (-2.718282,)),
            b"\xff\x01\x9e\xc6\xe4\x00\x33",
            [],
            [],
            marks=mark.xfail,
        ),
        (
            codegen.Instruction(
                codegen.OpCodes.LOAD_STRING, ("This is a jusτ a τεsτ string.",)
            ),
            b"\x00\x00\x00\x00\x00\x00\x00",
            [],
            [b"This is a jus\xcf\x84 a \xcf\x84\xce\xb5s\xcf\x84 string."],
        ),
        (
            codegen.Instruction(
                codegen.OpCodes.LOAD_FUNC,
                (
                    (
                        codegen.Instruction(codegen.OpCodes.LOAD_INT, (2,)),
                        codegen.Instruction(codegen.OpCodes.LOAD_INT, (5,)),
                        codegen.Instruction(codegen.OpCodes.NATIVE, (3,)),
                    ),
                ),
            ),
            b"\x00\x00\x00\x00\x00\x00\x00",
            [
                (
                    b"\x03\x00\x00\x00\x00\x02\x00\x00"
                    b"\x03\x00\x00\x00\x00\x05\x00\x00"
                    b"\x0b\x03\x00\x00\x00\x00\x00\x00"
                )
            ],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.BUILD_LIST, (200,)),
            b"\x00\x00\x00\xc8",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.BUILD_PAIR, ()),
            b"",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.LOAD_NAME, (3, 26)),
            b"\x00\x00\x03\x00\x00\x00\x1a",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.STORE_NAME, (10, 8)),
            b"\x00\x00\x0a\x00\x00\x00\x08",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.APPLY, ()),
            b"",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.NATIVE, (10,)),
            b"\x0a",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.JUMP, (12,)),
            b"\x00\x00\x00\x00\x00\x00\x0c",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.BRANCH, (52,)),
            b"\x00\x00\x00\x00\x00\x00\x34",
            [],
            [],
        ),
    ),
)
def test_encode_operands(
    instruction, expected_code, expected_func_pool, expected_string_pool
):
    actual_func_pool = []
    actual_string_pool = []
    actual_code = codegen.encode_operands(
        instruction.opcode, instruction.operands, actual_func_pool, actual_string_pool
    )
    assert expected_string_pool == actual_string_pool
    assert expected_func_pool == actual_func_pool
    assert len(actual_code) <= 7
    assert expected_code == actual_code


@mark.codegen
@mark.parametrize(
    "source,expected",
    (
        (b"", b""),
        (b"\x00", b"\x00"),
        (b"aaaabbcccccdeeeeeeeeee", b"\x04a\x02b\x05c\x01d\x0ae"),
    ),
)
def test_compress(source, expected):
    actual, _ = codegen.compress(source)
    assert expected == actual


@mark.codegen
@mark.parametrize(
    "source,expected",
    (
        (b"", ()),
        (b"\x00", ((1, b"\x00"),)),
        (
            b"aaaabbcccccdeeeeeeeeee",
            ((4, b"a"), (2, b"b"), (5, b"c"), (1, b"d"), (10, b"e")),
        ),
    ),
)
def test_generate_lengths(source, expected):
    actual_stream = codegen.generate_lengths(source)
    actual = tuple(actual_stream)
    assert expected == actual


@mark.codegen
@mark.parametrize(
    "stream,expected",
    (
        ((), b""),
        (((1, b"\x00"),), b"\x01\x00"),
        (
            ((4, b"a"), (2, b"b"), (5, b"c"), (1, b"d"), (10, b"e")),
            b"\x04a\x02b\x05c\x01d\x0ae",
        ),
        (
            ((265, b"x"), (16, b"y"), (782, b"z")),
            b"\xffx\x0ax\x10y\xffz\xffz\xffz\x11z",
        ),
    ),
)
def test_rebuild_stream(stream, expected):
    actual = codegen.rebuild_stream(stream)
    assert expected == actual


@mark.codegen
@mark.parametrize(
    "source,expected",
    (
        (
            "let negative_12 = -12",
            lowered.Define(
                lowered.Name("negative_12"),
                lowered.NativeOp(lowered.OperationTypes.NEG, lowered.Scalar(12)),
            ),
        ),
        (
            "let plus_one x = x + 1",
            lowered.Define(
                lowered.Name("plus_one"),
                lowered.Function(
                    lowered.Name("x"),
                    lowered.NativeOp(
                        lowered.OperationTypes.ADD,
                        lowered.Name("x"),
                        lowered.Scalar(1),
                    ),
                ),
            ),
        ),
        (
            "let () = ()",
            lowered.Unit(),
        ),
        (
            "let first (res, _) = res",
            lowered.Define(
                lowered.Name("first"),
                lowered.Function(
                    lowered.Name("$FuncParam_1"),
                    lowered.Block(
                        [
                            lowered.Define(
                                lowered.Name("res"),
                                lowered.Apply(
                                    lowered.Name("first"), lowered.Name("$FuncParam_1")
                                ),
                            ),
                            lowered.Apply(
                                lowered.Name("second"), lowered.Name("$FuncParam_1")
                            ),
                            lowered.Name("res"),
                        ],
                    ),
                ),
            ),
        ),
        (
            "let to_bool b = match b | True -> 1 | False -> 0",
            lowered.Define(
                lowered.Name("to_bool"),
                lowered.Function(
                    lowered.Name("b"),
                    lowered.Cond(
                        lowered.Name("b"), lowered.Scalar(1), lowered.Scalar(0)
                    ),
                ),
            ),
        ),
        (
            "let fib n = match n | 0 -> 1 | 1 -> 1 | _ -> fib (n-2) + fib (n-1)",
            lowered.Define(
                lowered.Name("fib"),
                lowered.Function(
                    lowered.Name("n"),
                    lowered.Cond(
                        lowered.NativeOp(
                            lowered.OperationTypes.EQUAL,
                            lowered.Scalar(0),
                            lowered.Name("n"),
                        ),
                        lowered.Scalar(1),
                        lowered.Cond(
                            lowered.NativeOp(
                                lowered.OperationTypes.EQUAL,
                                lowered.Scalar(1),
                                lowered.Name("n"),
                            ),
                            lowered.Scalar(1),
                            lowered.NativeOp(
                                lowered.OperationTypes.ADD,
                                lowered.Apply(
                                    lowered.Name("fib"),
                                    lowered.NativeOp(
                                        lowered.OperationTypes.SUB,
                                        lowered.Name("n"),
                                        lowered.Scalar(2),
                                    ),
                                ),
                                lowered.Apply(
                                    lowered.Name("fib"),
                                    lowered.NativeOp(
                                        lowered.OperationTypes.SUB,
                                        lowered.Name("n"),
                                        lowered.Scalar(1),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        (
            TAKE_SOURCE,
            lowered.Define(
                lowered.Name("take"),
                lowered.Function(
                    lowered.Name("$FuncParam_1"),
                    lowered.Block(
                        [
                            lowered.Define(
                                lowered.Name("seq"),
                                lowered.Apply(
                                    lowered.Name("first"), lowered.Name("$FuncParam_1")
                                ),
                            ),
                            lowered.Define(
                                lowered.Name("n"),
                                lowered.Apply(
                                    lowered.Name("second"), lowered.Name("$FuncParam_1")
                                ),
                            ),
                            lowered.Define(
                                lowered.Name("inner"),
                                lowered.Function(
                                    lowered.Name("$FuncParam_2"),
                                    lowered.Block(
                                        [
                                            lowered.Define(
                                                lowered.Name("seq_"),
                                                lowered.Apply(
                                                    lowered.Name("first"),
                                                    lowered.Name("$FuncParam_2"),
                                                ),
                                            ),
                                            lowered.Define(
                                                lowered.Name("n_"),
                                                lowered.Apply(
                                                    lowered.Name("first"),
                                                    lowered.Apply(
                                                        lowered.Name("second"),
                                                        lowered.Name("$FuncParam_2"),
                                                    ),
                                                ),
                                            ),
                                            lowered.Define(
                                                lowered.Name("cache"),
                                                lowered.Apply(
                                                    lowered.Name("second"),
                                                    lowered.Apply(
                                                        lowered.Name("second"),
                                                        lowered.Name("$FuncParam_2"),
                                                    ),
                                                ),
                                            ),
                                            lowered.Cond(
                                                lowered.NativeOp(
                                                    lowered.OperationTypes.EQUAL,
                                                    lowered.Apply(
                                                        lowered.Name("length"),
                                                        lowered.Name("seq_"),
                                                    ),
                                                    lowered.Scalar(0),
                                                ),
                                                lowered.Name("cache"),
                                                lowered.Block(
                                                    [
                                                        lowered.Define(
                                                            lowered.Name("x"),
                                                            lowered.Apply(
                                                                lowered.Name("at"),
                                                                lowered.Pair(
                                                                    lowered.Name(
                                                                        "seq_"
                                                                    ),
                                                                    lowered.Scalar(0),
                                                                ),
                                                            ),
                                                        ),
                                                        lowered.Define(
                                                            lowered.Name("xs"),
                                                            lowered.Apply(
                                                                lowered.Name("drop"),
                                                                lowered.Pair(
                                                                    lowered.Name(
                                                                        "seq_"
                                                                    ),
                                                                    lowered.Scalar(1),
                                                                ),
                                                            ),
                                                        ),
                                                        lowered.Cond(
                                                            lowered.NativeOp(
                                                                lowered.OperationTypes.GREATER,
                                                                lowered.Name("n"),
                                                                lowered.Scalar(0),
                                                            ),
                                                            lowered.Apply(
                                                                lowered.Name("inner"),
                                                                lowered.Pair(
                                                                    lowered.Name("xs"),
                                                                    lowered.Pair(
                                                                        lowered.NativeOp(
                                                                            lowered.OperationTypes.SUB,
                                                                            lowered.Name(
                                                                                "n"
                                                                            ),
                                                                            lowered.Scalar(
                                                                                1
                                                                            ),
                                                                        ),
                                                                        lowered.NativeOp(
                                                                            lowered.OperationTypes.JOIN,
                                                                            lowered.List(
                                                                                [
                                                                                    lowered.Name(
                                                                                        "x"
                                                                                    )
                                                                                ]
                                                                            ),
                                                                            lowered.Name(
                                                                                "cache"
                                                                            ),
                                                                        ),
                                                                    ),
                                                                ),
                                                            ),
                                                            lowered.Name("cache"),
                                                        ),
                                                    ]
                                                ),
                                            ),
                                        ]
                                    ),
                                ),
                            ),
                            lowered.Apply(
                                lowered.Name("inner"),
                                lowered.Pair(
                                    lowered.Name("seq"),
                                    lowered.Pair(
                                        lowered.Name("n"),
                                        lowered.List([]),
                                    ),
                                ),
                            ),
                        ]
                    ),
                ),
            ),
        ),
    ),
)
def test_simplify(source, expected):
    ast = _prepare(source)
    actual = codegen.simplify(ast)
    assert expected == actual

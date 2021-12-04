# pylint: disable=C0116
from pytest import mark, param

from context import codegen, lowered


@mark.codegen
@mark.parametrize(
    "kwargs,expected",
    (
        (
            {
                "stream_size": 111,
                "func_pool_size": 18,
                "string_pool_size": 53,
                "lib_mode": False,
                "encoding_used": "UTF8",
            },
            (
                b"M:\x00;F:\x00\x00\x00\x12;S:\x00\x00\x00\x35;C:\x00\x00\x00\x6f;"
                b"E:utf-8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00;"
            ),
        ),
        (
            {
                "stream_size": 1342,
                "func_pool_size": 84,
                "string_pool_size": 101,
                "lib_mode": True,
                "encoding_used": "Latin-1",
            },
            (
                b"M:\xff;F:\x00\x00\x00\x54;S:\x00\x00\x00\x65;C:\x00\x00\x00\x00;"
                b"E:iso8859-1\x00\x00\x00\x00\x00\x00\x00;"
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
            b"\x01\xff\x00\x00\x00\x00\x00\x00",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.LOAD_INT, (4200,)),
            b"\x03\x00\x00\x10\x68\x00\x00\x00",
            [],
            [],
        ),
        param(
            codegen.Instruction(codegen.OpCodes.LOAD_FLOAT, (-2.718282,)),
            b"\x02\xff\x01\x9e\xc6\xe4",
            [],
            [],
            marks=mark.xfail,
        ),
        # TODO: Implement a way to handle overflow errors when enocding
        #  floats.
        (
            codegen.Instruction(
                codegen.OpCodes.LOAD_STRING, ("This is a jusτ a τεsτ string.",)
            ),
            b"\x04\x00\x00\x00\x00\x00\x00\x00",
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
                        codegen.Instruction(codegen.OpCodes.NATIVE, (1,)),
                    ),
                ),
            ),
            b"\x05\x00\x00\x00\x00\x00\x00\x00",
            [
                (
                    b"\x03\x00\x00\x00\x02\x00\x00\x00"
                    b"\x03\x00\x00\x00\x05\x00\x00\x00"
                    b"\x0b\x00\x00\x00\x01\x00\x00\x00"
                )
            ],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.BUILD_LIST, (200,)),
            b"\x06\x00\x00\x00\xc8\x00\x00\x00",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.BUILD_TUPLE, (2,)),
            b"\x07\x00\x00\x00\x02\x00\x00\x00",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.LOAD_NAME, (3, 26)),
            b"\x08\x00\x00\x03\x00\x00\x00\x1a",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.STORE_NAME, (10, 8)),
            b"\x09\x00\x00\x0a\x00\x00\x00\x08",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.CALL, (5,)),
            b"\x0a\x05\x00\x00\x00\x00\x00\x00",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.NATIVE, (10,)),
            b"\x0b\x00\x00\x00\x0a\x00\x00\x00",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.JUMP, (12,)),
            b"\x0c\x00\x00\x00\x0c\x00\x00\x00",
            [],
            [],
        ),
        (
            codegen.Instruction(codegen.OpCodes.BRANCH, (52,)),
            b"\x0d\x00\x00\x00\x34\x00\x00\x00",
            [],
            [],
        ),
    ),
)
def test_encode(instruction, expected_code, expected_func_pool, expected_string_pool):
    actual_func_pool = []
    actual_string_pool = []
    actual_code = codegen.encode(
        instruction.opcode, instruction.operands, actual_func_pool, actual_string_pool
    )
    assert expected_string_pool == actual_string_pool
    assert expected_func_pool == actual_func_pool
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
    actual = codegen.compress(source)
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
def test_compress_stream(stream, expected):
    actual = codegen.compress_stream(stream)
    assert expected == actual

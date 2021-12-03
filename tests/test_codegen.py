# pylint: disable=C0116
from pytest import mark

from context import codegen


@mark.codegen
@mark.parametrize(
    "source,expected",
    (
        (b"", b""),
        (b"\x00", b"\x00"),
        (b"aaaabbcccccdeeeeeeeeee", b"\x04a\x02b\x05c\x01d\x0ae"),
    )
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
            b"\xffx\x0ax\x10y\xffz\xffz\xffz\x11z"
        ),
    ),
)
def test_compress_stream(stream, expected):
    actual = codegen.compress_stream(stream)
    assert expected == actual

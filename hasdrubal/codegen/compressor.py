from typing import Iterator, Tuple

from . import BYTE_ORDER


def compress(original: bytes) -> bytes:
    """
    Shrink down the bytecode by using a simple run-length encoding.

    Parameters
    ----------
    original: bytes
        The original uncompressed stream of bytes.

    Returns
    -------
    bytes
        The compressed version of `original`. If the compression results
        in a stream longer than `original` then `original` will be
        returned unchanged.
    """
    compressed = rebuild_stream(generate_lengths(original))
    return original if len(compressed) >= len(original) else compressed


def generate_lengths(source: bytes) -> Iterator[Tuple[int, bytes]]:
    """
    Generate the run lengths for each character for the encoder to use.

    Parameters
    ----------
    source: bytes
        The source text to be compressed.

    Returns
    -------
    Iterator[Tuple[int, bytes]]
        A stream of pairs of the run length and the character.
    """
    amount = 1
    prev_char = None
    char = -1
    for char in source:
        if char == prev_char:
            amount += 1
            continue

        if prev_char is not None:
            yield (amount, prev_char.to_bytes(1, BYTE_ORDER))
        amount = 1
        prev_char = char

    if char != -1:
        yield (amount, char.to_bytes(1, BYTE_ORDER))


def rebuild_stream(stream: Iterator[Tuple[int, bytes]]) -> bytes:
    """
    Re-constitute the stream from pairs of numbers and chars into a
    single `bytes` object.

    Parameters
    ----------
    stream: Iterator[Tuple[int, bytes]]
        The stream of run lengths and characters.

    Returns
    -------
    bytes
        The final byte stream.
    """
    return b"".join(
        amount.to_bytes(1, BYTE_ORDER) + char for amount, char in normalise(stream)
    )


def normalise(stream: Iterator[Tuple[int, bytes]]) -> Iterator[Tuple[int, bytes]]:
    """
    Ensure that there are no run lengths in the stream that can't be
    represented in a single byte.

    Parameters
    ----------
    stream: Iterator[Tuple[int, bytes]]
        A stream of run length and character pairs.

    Returns
    -------
    Iterator[Tuple[int, bytes]]
        The same stream but now all the run lengths are guaranteed to
        be representable in a single byte.
    """
    for amount, char in stream:
        while amount > 0xFF:
            yield (0xFF, char)
            amount -= 0xFF
        yield (amount, char)

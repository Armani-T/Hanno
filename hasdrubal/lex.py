from codecs import lookup
from enum import Enum, unique
from re import DOTALL, compile as re_compile
from sys import getfilesystemencoding
from typing import Callable, Iterator, Match, NamedTuple, Optional, Tuple, Union

from errors import BadEncodingError, IllegalCharError
from log import logger


# pylint: disable=C0103
@unique
class TokenTypes(Enum):
    equal = "="
    float_ = "float"
    in_ = "in"
    integer = "integer"
    let = "let"
    name = "name"
    newline = "\n"


DEFAULT_REGEX = re_compile(
    (
        r"(?P<float>(\d(\d|_)*)?\.\d(\d|_)*)"
        r"|(?P<integer>[0-9][0-9_]*)"
        r"|(?P<bool>\b(True|False)\b)"
        r"|(?P<name>[_a-z][_a-zA-Z0-9]*)"
        r"|(?P<type_name>[A-Z][_a-zA-Z0-9?]*)"
        r"|\.\.|/=|<=|>=|<>|\|>|<-|->|:=|=>"
        r'|"|\[|]|\(|\)|{|}|\||,|:|!|<|>|\+|-|\*|\^|/|%|\.|=|;|\\'
        r"|(?P<block_comment>###.*?###)"
        r"|(?P<line_comment>#.*?(\r\n|\n|\r|$))"
        r"|(?P<newline>(\r\n|\n|\r))"
        r"|(?P<whitespace>\s+)"
        r"|(?P<invalid>.)"
    ),
    DOTALL,
)

Token = NamedTuple(
    "Token",
    (("span", Tuple[int, int]), ("type_", TokenTypes), ("value", Optional[str])),
)
Stream = Iterator[Token]
RescueFunc = Callable[
    [bytes, Union[UnicodeDecodeError, UnicodeEncodeError]], Optional[str]
]

keywords = (TokenTypes.let, TokenTypes.in_)
literals = (TokenTypes.float_, TokenTypes.integer, TokenTypes.name)


def try_filesys_encoding(source: bytes, _: object) -> Optional[str]:
    """
    Try to recover the source by using the file system's encoding to
    decode it. The `_` argument is there because `to_utf8` expects a
    rescue function that takes at least 2 arguments.

    Parameters
    ----------
    source: bytes
        The source code which cannot be decoded using the default UTF-8
        encoding.
    _: object
        An argument that is ignored. Just pass `None` to avoid the
        `TypeError`.

    Returns
    -------
    Optional[str]
        If it is `None` then we are completely abandoning this attempt.
        If it is `str` then the rescue attempt succeeded and we will now
        this string.
    """
    fs_encoding = getfilesystemencoding()
    try:
        return source.decode(fs_encoding).encode("utf-8").decode("utf-8")
    except UnicodeEncodeError:
        logger.exception(
            "Unable to convert the source into UTF-8 bytes from a %s string.",
            fs_encoding,
            exc_info=True,
            stack_info=True,
        )
        return None
    except UnicodeDecodeError as error:
        logger.exception(
            "Unable to convert the source into a UTF-8 string from %s bytes.",
            error.encoding,
            exc_info=True,
            stack_info=True,
        )
        return None


def to_utf8(
    source: bytes,
    encoding: Optional[str] = None,
    rescue: RescueFunc = try_filesys_encoding,
) -> str:
    """
    Try to convert `source` to a string encoded using `encoding`.

    Parameters
    ----------
    source: bytes
        The source code which will be decoded to a string for lexing.
    encoding: Optional[str] = None
        The encoding that will be used to decode `source`. If it is
        `None`, then the function will use UTF-8.
    rescue: RescueFunc = try_filesys_encoding
        The function that will be called if this function encounters
        an error while trying to convert the source. If that function
        returns `None` then the error that was encountered originally
        will be raised, otherwise the string result will be returned.

    Returns
    -------
    str
        The source code which will now be used in lexing. It is
        guaranteed to be in UTF-8 format.
    """
    try:
        encoding = "utf-8" if encoding is None else lookup(encoding).name
        result = (
            source if encoding == "utf-8" else source.decode(encoding).encode(encoding)
        )
        result = result.decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError) as error:
        logger.exception(
            (
                "Unable to convert the source to a UTF-8 string using %s encoding. "
                "Attempting to rescue using `%s`"
            ),
            encoding,
            rescue.__name__,
            exc_info=True,
            stack_info=True,
        )
        result = rescue(source, error)
        if result is None:
            logger.info("The rescue function failed.")
            raise BadEncodingError() from error
        logger.info("Succeeded using the rescue function.")
        return result
    else:
        logger.info(
            "Succeeded using encoding `%s` without the rescue function.", encoding
        )
        return result

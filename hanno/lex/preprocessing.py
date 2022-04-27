from codecs import lookup
from sys import getfilesystemencoding
from typing import Callable, Collection, Optional

from errors import BadEncodingError, IllegalCharError
from log import logger

RescueFunc = Callable[[bytes, UnicodeError], Optional[str]]

try_filesys_encoding: RescueFunc

ALL_NEWLINE_TYPES: Collection[str] = ("\r\n", "\r", "\n")


def try_filesys_encoding(source, _):
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
        )
        return None
    except UnicodeDecodeError as error:
        logger.exception(
            "Unable to convert the source into a UTF-8 string from %s bytes.",
            error.encoding,
            exc_info=True,
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
        result_string = result.decode("utf-8")
    except UnicodeError as error:
        logger.exception(
            (
                "Unable to convert the source to a UTF-8 string using %s encoding. "
                "Attempting to rescue using `%s`"
            ),
            encoding,
            rescue.__name__,
            exc_info=True,
        )
        possible_result = rescue(source, error)
        if possible_result is None:
            logger.info("The rescue function failed.")
            # pylint: disable=E1101
            raise BadEncodingError(error.encoding) from error
        logger.info("Succeeded using the rescue function.")
        return possible_result
    else:
        logger.info(
            "Succeeded using encoding `%s` without the rescue function.", encoding
        )
        return result_string


def normalise_newlines(
    source: str,
    accepted_types: Collection[str] = ALL_NEWLINE_TYPES,
) -> str:
    """

    Normalise the newlines in the source code.

    This is so that they only have one type of newline (which is easier
     to handle, rather than 3 different OS-dependent types.

     Notes
     ----
     - "\\n" will always be accepted, whether it is in
       `accepted_types` or not.

    Parameters
    ----------
    source: str
        The source code with all sorts of newlines.
    accepted_types: Collection[str] = ALL_NEWLINE_TYPES
        The newline formats that will be accepted. If an invalid
        format is found, it will be rejected with an error.

    Returns
    -------
    str
        The source code with normalised newline formats.
    """
    for type_ in ALL_NEWLINE_TYPES:
        if type_ == "\n":
            continue
        if type_ in accepted_types:
            source = source.replace(type_, "\n")
        else:
            pos = source.find(type_)
            if pos != -1:
                logger.critical(
                    "Rejected newline (%r) found at position: %d", type_, pos
                )
                raise IllegalCharError((pos, pos + 1), type_)
    return source

from codecs import lookup

from sys import getfilesystemencoding
from typing import Callable, Optional

from .errors import BadEncodingError

RescueFunc = Callable[[bytes, UnicodeDecodeError], Optional[str]]


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
        return source.decode(fs_encoding).encode("utf8").decode("utf8")
    except (UnicodeEncodeError, UnicodeDecodeError):
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
            source.decode(encoding).encode(encoding) if encoding != "utf-8" else source
        )
        return result.decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError) as error:
        result = rescue(source, error)
        if result is None:
            raise BadEncodingError() from error
        return result

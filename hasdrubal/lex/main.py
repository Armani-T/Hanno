from string import whitespace
from typing import (
    Container,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Tuple,
)

from errors import (
    IllegalCharError,
    UnexpectedEOFError,
    UnexpectedTokenError,
)
from log import logger
from .tokens import DOUBLE_CHAR_TOKENS, KEYWORDS, SINGLE_CHAR_TOKENS, TokenTypes

Token = NamedTuple(
    "Token",
    (("span", Tuple[int, int]), ("type_", TokenTypes), ("value", Optional[str])),
)

Stream = Iterator[Token]

COMMENT_MARKER: str = "#"
WHITESPACE: Container[str] = whitespace

_is_name_char = lambda char: char.isalnum() or char == "_"


def _is_keyword(word: str) -> bool:
    for keyword in KEYWORDS:
        if keyword.value == word:
            return True
    return False


def _is_double_char_token(text: str) -> bool:
    for type_ in DOUBLE_CHAR_TOKENS:
        if text == type_.value:
            return True
    return False


def _is_single_char_token(text: str) -> bool:
    for type_ in SINGLE_CHAR_TOKENS:
        if text == type_.value:
            return True
    return False


def lex(source: str) -> "TokenStream":
    """
    Create a `TokenStream` using source for the parser to use.

    Parameters
    ----------
    source: str
        Where the tokens will cole from.

    Returns
    -------
    TokenStream
        The resulting tokens.
    """
    return TokenStream(generate_tokens(source), [TokenTypes.comment])


def generate_tokens(source: str) -> Stream:
    """Lazily go through `source` and break it up into many tokens."""
    prev_end = 0
    source_length = len(source)
    while prev_end < source_length:
        result = lex_word(source[prev_end:])
        if result is None:
            raise IllegalCharError((prev_end, prev_end + 1), source[prev_end])

        token_type, value, length = result
        start = prev_end
        prev_end += length
        yield Token((start, prev_end), token_type, value)


def lex_word(source: str) -> Optional[Tuple[TokenTypes, Optional[str], int]]:
    """Create the data required to build a single lexeme."""
    first = source[0]
    if first.isdecimal():
        return lex_number(source)
    if first.isalpha() or first == "_":
        return lex_name(source)
    if first == '"':
        return lex_string(source)
    if _is_double_char_token(source[:2]):
        return TokenTypes(source[:2]), None, 2
    if _is_single_char_token(first):
        return TokenTypes(first), None, 1
    if first == COMMENT_MARKER:
        return lex_comment(source)
    if first in WHITESPACE:
        return lex_whitespace(source)
    return None


def lex_comment(source: str) -> Tuple[TokenTypes, str, int]:
    """Lex a single line comment."""
    max_index = len(source)
    current_index = 0
    while current_index < max_index and source[current_index] != "\n":
        current_index += 1

    current_index += 1 if current_index < max_index else 0
    return TokenTypes.comment, source[:current_index], current_index


def lex_string(source: str) -> Optional[Tuple[TokenTypes, str, int]]:
    """
    Parse the (truncated) source in order to create a string token.

    Parameters
    ---------
    source: str
        The source code that will be lexed.

    Returns
    -------
    Optional[Tuple[TokenTypes, str, int]]
        If it is `None`, then it was unable to parse the source. Else,
        it is a tuple of (specifically) `TokenTypes.string`, then
        the actual string parsed and its length.
    """
    current_index = 1
    in_escape = False
    max_index = len(source)
    while current_index < max_index:
        if (not in_escape) and source[current_index] == '"':
            break

        in_escape = (not in_escape) if source[current_index] == "\\" else False
        current_index += 1
    else:
        logger.critical(
            "The stream unexpectedly ended before finding the end of the string."
        )
        return None

    current_index += 1
    return TokenTypes.string, source[:current_index], current_index


def lex_name(source: str) -> Tuple[TokenTypes, Optional[str], int]:
    """
    Parse the (truncated) source in order to create either a `name`
    or a keyword token.

    Parameters
    ---------
    source: str
        The source code that will be lexed.

    Returns
    -------
    Tuple[TokenTypes, Optional[str], int]
        It is a tuple of either a keyword token type or
        `TokenTypes.name`, then the actual name parsed (or `None` if
        it's a keyword) and its length.
    """
    max_index = len(source)
    current_index = 0
    while current_index < max_index and _is_name_char(source[current_index]):
        current_index += 1

    token_value = source[:current_index]
    if _is_keyword(token_value):
        return TokenTypes(token_value), None, current_index
    return TokenTypes.name_, token_value, current_index


def lex_number(source: str) -> Tuple[TokenTypes, str, int]:
    """
    Parse the (truncated) source in order to create either an `integer`
    or a `float_` token.

    Parameters
    ---------
    source: str
        The source code that will be lexed.

    Returns
    -------
    Tuple[TokenTypes, str, int]
        It is a tuple of (specifically) either `TokenTypes.integer` or
        `TokenTypes.float_`, then the actual string parsed and its
        length.
    """
    max_index = len(source)
    current_index = 0
    type_ = TokenTypes.integer
    while current_index < max_index and source[current_index].isdecimal():
        current_index += 1

    if current_index < max_index and source[current_index] == ".":
        current_index += 1
        type_ = TokenTypes.float_
        while current_index < max_index and source[current_index].isdecimal():
            current_index += 1

    return type_, source[:current_index], current_index


def lex_whitespace(source: str) -> Tuple[TokenTypes, str, int]:
    """Lex either a `whitespace` or a `newline` token."""
    max_index = len(source)
    current_index = 0
    while current_index < max_index and source[current_index] in WHITESPACE:
        current_index += 1
    return TokenTypes.whitespace, source[:current_index], current_index


class TokenStream:
    """
    A wrapper class around the token generator so that we can preserve
    already computed elements and integrate with the parser which
    expects an eager lexer.

    Warnings
    --------
    - This class contains a lot of mutable state so it absolutely is
      not thread-safe.
    - The class' equality check exhausts the iterator so you should be
      very careful about using it.
    """

    __slots__ = ("_cache", "_generator", "_produced_eof", "ignore")

    def __init__(
        self, generator: Iterator[Token], ignore: Container[TokenTypes]
    ) -> None:
        self._cache: List[Token] = []
        self._generator: Iterator[Token] = generator
        self._produced_eof: bool = False
        self.ignore: Container[TokenTypes] = ignore

    def consume(self, *expected: TokenTypes) -> Token:
        """
        Check if the next token is in `expected` and if it is, return
        the token at the head and _advance the stream. If it's not in
        the stream, raise an error.

        Returns
        -------
        Token
            The token at the head of the stream.
        """
        head = self._advance()
        if head.type_ in expected:
            return head
        logger.critical("Tried consuming expected %s but got %s", expected, head)
        raise UnexpectedTokenError(head, *expected)

    def consume_if(self, *expected: TokenTypes) -> bool:
        """
        Check if the next token is in `expected` and if it is, _advance
        one step through the stream. Otherwise, keep the stream as is.

        Parameters
        ----------
        *expected: TokenTypes
            It is expected that the `type_` attr of tokens at the head
            of `stream` should be one of these.

        Raises
        ------
        error.StreamOverError
            There is nothing left in the `stream` so we can't _advance
            it.

        Returns
        -------
        bool
            Whether `expected` was found at the front of the stream.
        """
        head = self._advance()
        if head.type_ in expected:
            return True
        self._cache.append(head)
        return False

    def peek(self, *expected: TokenTypes) -> bool:
        """
        Check if `expected` is the next token without advancing the
        stream.

        Warnings
        --------
        - If the stream is empty, then `False` will be returned.

        Parameters
        ----------
        *expected: TokenTypes
            It is expected that the `type_` attr of tokens at the head
            of `stream` should be one of these.

        Returns
        -------
        bool
            Whether `expected` was found at the front of the stream.
        """
        try:
            token = self.preview()
            return token is not None and token.type_ in expected
        except UnexpectedEOFError:
            return False

    def preview(self) -> Optional[Token]:
        """
        View the token at the head of the stream without letting the
        stream forget about it or return `None` if the stream is empty.

        Returns
        -------
        Token
            The token at the head of the stream.
        """
        try:
            head = self._advance()
            self._cache.append(head)
            return head
        except UnexpectedEOFError:
            return None

    def show(self) -> str:
        """Pretty print all the tokens within."""
        parts = []
        for token in self:
            span = f"{token.span[0]}-{token.span[1]}"
            parts.append(
                f"[ #{span} {token.type_.name} ]"
                if token.value is None
                else f'[ #{span} {token.type_.name} "{token.value}" ]'
            )
        return "\n".join(parts)

    def _advance(self) -> Token:
        """Move the stream forward one step."""
        if self._cache:
            return self._cache.pop()

        result = next(self._generator, None)
        if result is None:
            if self._produced_eof:
                logger.critical("Runtime requested lexer for 2+ EOF tokens.")
                raise UnexpectedEOFError()

            self._produced_eof = True
            result = Token((0, 0), TokenTypes.eof, None)
            logger.debug("Stream over. EOF token has been produced.")

        return result if result in self.ignore else self._advance()

    def __bool__(self):
        return self.preview() is not None

    def __eq__(self, other):
        return all(
            self_token == other_token for self_token, other_token in zip(self, other)
        )

    def __iter__(self):
        token = self._advance()
        while token is not None:
            yield token
            token = self._advance()

    def __next__(self):
        try:
            return self._advance()
        except UnexpectedEOFError as error:
            raise StopIteration() from error

from enum import Enum, unique
from string import whitespace
from typing import (
    Collection,
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


# pylint: disable=C0103
@unique
class TokenTypes(Enum):
    """
    All the possible types that a token from this lexer can have.

    They are organised into 2 groups:
    - The upper group is made up of token types whose tokens will have
      `token.value: str`.
    - The lower group is made up of token types whose tokens will have
      `token.value = None`.
    """

    block_comment = "###"
    float_ = "float"
    line_comment = "#"
    integer = "integer"
    name_ = "name"
    string = "string"

    and_ = "and"
    else_ = "else"
    end = "end"
    eof = "<eof>"
    eol = "<eol>"
    false = "False"
    if_ = "if"
    let = "let"
    not_ = "not"
    or_ = "or"
    then = "then"
    true = "True"
    whitespace = " "

    arrow = "->"
    asterisk = "*"
    bslash = "\\"
    caret = "^"
    colon = ":"
    colon_equal = ":="
    comma = ","
    dash = "-"
    diamond = "<>"
    dot = "."
    equal = "="
    fslash = "/"
    fslash_equal = "/="
    greater = ">"
    greater_equal = ">="
    lbracket = "["
    less = "<"
    less_equal = "<="
    lparen = "("
    newline = "\n"
    percent = "%"
    plus = "+"
    rbracket = "]"
    rparen = ")"


Token = NamedTuple(
    "Token",
    (("span", Tuple[int, int]), ("type_", TokenTypes), ("value", Optional[str])),
)

Stream = Iterator[Token]

IGNORED_TOKENS: Container[TokenTypes] = (
    TokenTypes.block_comment,
    TokenTypes.line_comment,
    TokenTypes.whitespace,
)
KEYWORDS: Collection[TokenTypes] = (
    TokenTypes.and_,
    TokenTypes.else_,
    TokenTypes.end,
    TokenTypes.false,
    TokenTypes.if_,
    TokenTypes.let,
    TokenTypes.not_,
    TokenTypes.or_,
    TokenTypes.then,
    TokenTypes.true,
)
SINGLE_CHAR_TOKENS: Collection[TokenTypes] = (
    TokenTypes.asterisk,
    TokenTypes.bslash,
    TokenTypes.caret,
    TokenTypes.colon,
    TokenTypes.comma,
    TokenTypes.dash,
    TokenTypes.dot,
    TokenTypes.equal,
    TokenTypes.fslash,
    TokenTypes.greater,
    TokenTypes.lbracket,
    TokenTypes.less,
    TokenTypes.lparen,
    TokenTypes.newline,
    TokenTypes.percent,
    TokenTypes.plus,
    TokenTypes.rbracket,
    TokenTypes.rparen,
)
DOUBLE_CHAR_TOKENS: Collection[TokenTypes] = (
    TokenTypes.arrow,
    TokenTypes.colon_equal,
    TokenTypes.diamond,
    TokenTypes.fslash_equal,
    TokenTypes.greater_equal,
    TokenTypes.less_equal,
)

BLOCK_COMMENT_MARKER: str = "###"
LINE_COMMENT_MARKER: str = "#"
WHITESPACE: Container[str] = whitespace

_is_name_char = lambda char: char.isalnum() or char == "_"


def lex(source: str) -> Stream:
    """
    Generate a stream of tokens for the parser to build an AST with.

    WARNING: The tokens produces `newline` tokens which the parser
      doesn't know how to handle. You should pass the list through
      `infer_eols` first.

    Parameters
    ----------
    source: str
        The string that will be lexed.

    Returns
    -------
    Stream
        The tokens that were made.
    """
    prev_end = 0
    source_length = len(source)
    while prev_end < source_length:
        result = lex_word(source[prev_end:])
        if result is None:
            raise IllegalCharError((prev_end, prev_end + 1), source[prev_end])

        token_type, value, length = result
        start, prev_end = prev_end, prev_end + length
        if token_type not in IGNORED_TOKENS:
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
    if first in WHITESPACE:
        return lex_whitespace(source)
    return lex_comment(source)


def _is_single_char_token(text: str) -> bool:
    for type_ in SINGLE_CHAR_TOKENS:
        if text == type_.value:
            return True
    return False


def _is_double_char_token(text: str) -> bool:
    for type_ in DOUBLE_CHAR_TOKENS:
        if text == type_.value:
            return True
    return False


def lex_whitespace(source: str) -> Tuple[TokenTypes, None, int]:
    """Lex either a `whitespace` or a `newline` token."""
    max_index = len(source)
    current_index = 0
    is_newline = False
    while current_index < max_index and source[current_index] == "\n":
        is_newline = True
        current_index += 1

    if is_newline:
        return TokenTypes.newline, None, current_index

    while current_index < max_index and source[current_index] in WHITESPACE:
        current_index += 1
    return TokenTypes.whitespace, None, current_index


# TODO: Implement nesting for block comments.
def lex_block_comment(source: str) -> Tuple[TokenTypes, str, int]:
    """Lex a single block comment."""
    start = 0
    section = source[start : start + 3]
    section_size = len(section)
    while section_size == 3 and section != BLOCK_COMMENT_MARKER:
        start += 1
        section = source[start : start + 3]
        section_size = len(section)

    length = start + 3
    return TokenTypes.block_comment, source[:length], length


def lex_comment(source: str) -> Optional[Tuple[TokenTypes, str, int]]:
    """
    Parse the next part of the source to decide whether there is a
    comment present.

    Parameters
    ---------
    source: str
        The source code that will be lexed.

    Returns
    -------
    Tuple[TokenTypes, Optional[str], int]
        If it is not `None`, then it is a `TokenTypes.block_comment` or
        `TokenTypes.line_comment` followed by the comment text and its
        length. If it is `None`, then no comment was found.
    """
    if source[:3] == BLOCK_COMMENT_MARKER:
        return lex_block_comment(source)
    if source[0] == LINE_COMMENT_MARKER:
        return lex_line_comment(source)
    return None


# TODO: Implement nesting for block comments.
def lex_line_comment(source: str) -> Tuple[TokenTypes, str, int]:
    """Lex a single line comment."""
    max_index = len(source)
    current_index = 0
    while current_index < max_index and source[current_index] != "\n":
        current_index += 1

    current_index += 1 if current_index < max_index else 0
    return TokenTypes.line_comment, source[:current_index], current_index


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


def _is_keyword(word: str) -> bool:
    for keyword in KEYWORDS:
        if keyword.value == word:
            return True
    return False


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


def show_tokens(stream: Stream) -> str:
    """
    Pretty print the tokens produced by the lexer.

    Parameters
    ----------
    stream: Stream
        The tokens produced by the lexer.

    Returns
    -------
    str
        The result of pretty printing the tokens.
    """

    def inner(token):
        span = f"{token.span[0]}-{token.span[1]}"
        if token.value is None:
            return f"[ #{span} {token.type_.name} ]"
        return f'[ #{span} {token.type_.name} "{token.value}" ]'

    return "\n".join(map(inner, stream))


class TokenStream:
    """
    A wrapper class around the token generator so that we can preserve
    already computed elements and integrate with the parser which
    expects an eager lexer.

    Warnings
    --------
    - This class contains a lot of mutable state so the best way to use
      it is by having a separate copy for each thread.
    """

    __slots__ = ("_cache", "_generator", "_produced_eof")

    def __init__(self, generator: Iterator[Token]) -> None:
        self._cache: List[Token] = []
        self._generator: Iterator[Token] = generator
        self._produced_eof: bool = False

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
        self._push(head)
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
            self._push(head)
            return head
        except UnexpectedEOFError:
            return None

    def _advance(self) -> Token:
        """
        Move the stream forward one step.

        Raises
        ------
        error.StreamOverError
            There is nothing left in the `stream` so we can't _advance
            it.

        Returns
        -------
        Token
            The token at the head of the stream.
        """
        if self._cache:
            return self._pop()

        result = next(self._generator, None)
        if result is None:
            if self._produced_eof:
                raise UnexpectedEOFError()

            self._produced_eof = True
            result = Token((0, 0), TokenTypes.eof, None)
        return result

    def _pop(self) -> Token:
        return self._cache.pop()

    def _push(self, token: Token) -> None:
        self._cache.append(token)

    def __bool__(self) -> bool:
        try:
            if self._cache or not self._produced_eof:
                return True
            self._push(self._advance())
            return True
        except UnexpectedEOFError:
            return False

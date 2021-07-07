from codecs import lookup
from enum import Enum, unique
from re import DOTALL, compile as re_compile
from sys import getfilesystemencoding
from typing import (
    Container,
    Callable,
    Iterator,
    List,
    Match,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

from errors import (
    BadEncodingError,
    IllegalCharError,
    UnexpectedEOFError,
    UnexpectedTokenError,
)
from log import logger


# pylint: disable=C0103
@unique
class TokenTypes(Enum):
    """
    All the possible values that a lexer token can be.

    They are organised into 2 groups:
    - The upper group is made up of token types whose tokens have
      `value`s of type `str`.
    - The lower group is made up of token types whole tokens have
      `None` as their string value.
    """

    comment = "###"
    eol = "<eol>"
    float_ = "float"
    integer = "integer"
    name = "name"
    string = "string"

    and_ = "and"
    else_ = "else"
    false = "False"
    if_ = "if"
    in_ = "in"
    let = "let"
    not_ = "not"
    or_ = "or"
    then = "then"
    true = "True"

    arrow = "->"
    asterisk = "*"
    bslash = "\\"
    caret = "^"
    comma = ","
    dash = "-"
    diamond = "<>"
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
    pipe_greater = "|>"
    plus = "+"
    rbracket = "]"
    rparen = ")"


DEFAULT_REGEX = re_compile(
    (
        r"(?P<float>\d(\d|_)*\.\d(\d|_)*)"
        r"|(?P<integer>\d(\d|_)*)"
        r"|(?P<name>[_A-Za-z][_a-zA-Z0-9]*)"
        r"|<>|/=|\|>|>=|<=|->"
        r'|"|\[|]|\(|\)|<|>|=|,|-|/|%|\+|\*|\\|\^'
        r"|(?P<comment>#.*?(\r\n|\n|\r|$))"
        r"|(?P<crlf_newline>(\r\n)+)"
        r"|(?P<lf_newline>\n+)"
        r"|(?P<cr_newline>\r+)"
        r"|(?P<whitespace>\s+)"
        r"|(?P<invalid>.)"
    ),
    DOTALL,
)

Token = NamedTuple(
    "Token",
    (("span", Tuple[int, int]), ("type_", TokenTypes), ("value", Optional[str])),
)

EOLCheckFunc = Callable[[Token, Optional[Token], int], bool]
Stream = Iterator[Token]
RescueFunc = Callable[
    [bytes, Union[UnicodeDecodeError, UnicodeEncodeError]], Optional[str]
]

all_newlines = ("crlf_newline", "cr_newline", "lf_newline")

literals = (TokenTypes.float_, TokenTypes.integer, TokenTypes.name, TokenTypes.string)
keywords = (
    TokenTypes.and_,
    TokenTypes.else_,
    TokenTypes.false,
    TokenTypes.if_,
    TokenTypes.in_,
    TokenTypes.let,
    TokenTypes.not_,
    TokenTypes.or_,
    TokenTypes.then,
    TokenTypes.true,
)

valid_enders = (*literals, TokenTypes.rparen, TokenTypes.rbracket)
valid_starters = (TokenTypes.let, TokenTypes.lparen, TokenTypes.lbracket, *literals)


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
        result_string = result.decode("utf-8")
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
        possible_result = rescue(source, error)
        if possible_result is None:
            logger.info("The rescue function failed.")
            raise BadEncodingError() from error
        logger.info("Succeeded using the rescue function.")
        return possible_result
    else:
        logger.info(
            "Succeeded using encoding `%s` without the rescue function.", encoding
        )
        return result_string


def lex(source: str, regex=DEFAULT_REGEX) -> Stream:
    """
    Generate a stream of tokens for the parser to build an AST with.

    WARNING: The tokens produces `newline` tokens which the parser
      doesn't know how to handle. You should pass the list through
      `infer_eols` first.

    Parameters
    ----------
    source: str
        The string that will be lexed.
    regex: Pattern[str] = DEFAULT_REGEX
        A compiled regex that will be used to match parts of `source`
        for making tokens.

    Returns
    -------
    Stream
        The tokens that were made.
    """
    prev_end = 0
    source_length = len(source)
    while prev_end < source_length:
        match = regex.match(source, prev_end)
        if match is not None:
            token = build_token(match, source)
            prev_end = match.end()
            if token is not None:
                yield token
        else:
            logger.warning("Created a `None` instead of match at pos %d", prev_end)


def build_token(
    match: Optional[Match[str]],
    source: str,
    accepted_newlines: Container[str] = all_newlines,
) -> Optional[Token]:
    """
    Turn a `Match` object into either a `Token` object or `None`.

    Parameters
    ----------
    match: Optional[Match[str]]
        The match object that this function converts.
    source: str
        The source code that will be lexed.
    accepted_newlines: Container[str] = all_newlines
        The newline formats that are valid to the lexer. If an invalid
        format is given, it will be rejected with an error.

    Returns
    -------
    Optional[Token]
        If it's `None` then it's because the returned token should be
        ignored.
    """
    if match is None:
        return None

    rejected_newlines = [
        token_type for token_type in all_newlines if token_type not in accepted_newlines
    ]
    literals_str = [lit.value for lit in literals]
    keywords_str = [keyword.value for keyword in keywords]
    type_, text, span = match.lastgroup, match[0], match.span()
    if type_ == "illegal_char":
        logger.critical("Invalid match object: `%r`", match)
        raise IllegalCharError(span[0], text)
    if type_ in rejected_newlines:
        logger.critical("Rejected newline format: %r", text)
        raise IllegalCharError(span[0], text)
    if type_ == "whitespace":
        return None
    if text == '"':
        return lex_string(span[0], source)
    if type_ == "name":
        is_keyword = text in keywords_str
        token_type = TokenTypes(text) if is_keyword else TokenTypes.name
        return Token(span, token_type, None if is_keyword else text)
    if type_ == "comment" or type_ in accepted_newlines:
        return Token(span, TokenTypes(type_), None)
    if type_ in literals_str:
        return Token(span, TokenTypes(type_), text)
    return Token(span, TokenTypes(text), None)


def lex_string(start: int, source: str) -> Token:
    """
    Parse the source text to figure out where a string token should end
    since strings can get weird in that they can contain escapes inside
    their bodies.

    Parameters
    ---------
    start: int
        The point at which the initial `"` marker was found so it can
        be used as the starting point of the string parser.
    source: str
        The source code that will be lexed.

    Returns
    -------
    Tuple[int, Token]
        The tuple is made up of the position from which the
        regex matcher should continue in the next iteration and the
        token it has just made.
    """
    in_escape = False
    current = start + 1
    max_current_size = len(source)
    while current < max_current_size:
        if (not in_escape) and source[current] == '"':
            break
        in_escape = False
        if source[current] == "\\":
            in_escape = not in_escape
        current += 1
    else:
        logger.critical(
            "The stream unexpectedly ended before finding the end of the string."
        )
        raise IllegalCharError(start, '"')
    return Token((start, current + 1), TokenTypes.string, source[start:current])


def can_add_eol(prev: Token, next_: Optional[Token], stack_size: int) -> bool:
    """
    Check whether an EOL token can be added at the current position.

    Parameters
    ----------
    prev: Token
        The tokens present in the raw stream that came from the lexer.
    next_: Stream
        The next token in the stream, or `None` if the stream is empty.
    stack_size: int
        If it's `!= 0`, then there are enclosing brackets/parentheses.

    Returns
    -------
    bool
        Whether or not to add an EOL token at the current position.
    """
    return (
        stack_size == 0
        and (prev.type_ in valid_enders)
        and (next_ is None or next_.type_ in valid_starters)
    )


def infer_eols(stream: Stream, can_add: EOLCheckFunc = can_add_eol) -> Stream:
    """
    Replace `newline` with `eol` tokens, as needed, in the stream.

    Parameters
    ----------
    stream: Stream
        The raw stream straight from the lexer.
    can_add: EOLCheckFunc = default_can_add
        The function that decides whether or not to add an EOL at the
        current position.

    Returns
    -------
    Stream
        The stream with the inferred eols.
    """
    openers = (TokenTypes.lbracket, TokenTypes.lparen)
    closers = (TokenTypes.rbracket, TokenTypes.rparen)
    paren_stack_size = 0
    token = prev_token = Token((0, 1), TokenTypes.eol, None)
    has_run = False
    for token in stream:
        has_run = True
        if token.type_ == TokenTypes.newline:
            next_token: Optional[Token] = next(stream, None)
            if can_add(prev_token, next_token, paren_stack_size):
                yield Token(
                    (prev_token.span[1], next_token.span[0]), TokenTypes.eol, None
                )
            if next_token is None:
                break
            token = next_token
        elif token.type_ in openers:
            paren_stack_size += 1
        elif token.type_ in closers:
            paren_stack_size -= 1
        yield token
        prev_token = token

    if has_run and token.type_ != TokenTypes.newline:
        span_start = token.span[1]
        yield Token((span_start, span_start + 1), TokenTypes.eol, None)


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
    pprint_token = lambda token: (
        f"[ {token.span[0]}-{token.span[1]} {token.type_.name} ]"
        if token.value is None
        else f'[ {token.span[0]}-{token.span[1]} {token.type_.name} "{token.value}" ]'
    )
    return "\n".join(map(pprint_token, stream))


class TokenStream:
    """
    A wrapper class around the token generator so that we can preserve
    already computed elements and integrate with the parser which
    expects an eager lexer.
    """

    __slots__ = ("_cache", "_generator")

    def __init__(self, generator: Iterator[Token]) -> None:
        self._cache: List[Token] = []
        self._generator: Iterator[Token] = generator

    def advance(self) -> Token:
        """
        Move the stream forward one step.

        Raises
        ------
        error.StreamOverError
            There is nothing left in the `stream` so we can't advance it.

        Returns
        -------
        Token
            The token at the head of the stream.
        """
        try:
            return self._cache.pop() if self._cache else next(self._generator)
        except StopIteration as error:
            raise UnexpectedEOFError from error

    def consume(self, *expected: TokenTypes) -> None:
        """
        Check if the next token is in `expected` and if it is, advance
        the stream. If it's not in the stream, raise an error.

        Parameters
        ----------
        *expected: TokenTypes
            It is expected that the `type_` attr of tokens at the head
            of `stream` should be one of these.

        Raises
        ------
        error.StreamOverError
            There is nothing left in the `stream` so we can't advance it.
        error.UnexpectedTokenError
            Nothing in `expected` was found at the front of `stream`.
        """
        head = self.advance()
        if head.type_ not in expected:
            logger.critical("Tried consuming %s but got %s", expected, head)
            raise UnexpectedTokenError(head, *expected)

    def consume_if(self, *expected: TokenTypes) -> bool:
        """
        Check if the next token is in `expected` and if it is, advance
        one step through the stream. Otherwise, keep the stream as is.

        Parameters
        ----------
        *expected: TokenTypes
            It is expected that the `type_` attr of tokens at the head
            of `stream` should be one of these.

        Raises
        ------
        error.StreamOverError
            There is nothing left in the `stream` so we can't advance it.

        Returns
        -------
        bool
            Whether `expected` was found at the front of the stream.
        """
        if self.peek(*expected):
            self.advance()
            return True
        return False

    def consume_get(self, *expected: TokenTypes) -> Token:
        """
        Do the same thing as `advance` but first check if the token is
        in `expected` and throw an error if it isn't.

        Parameters
        ----------
        *expected: TokenTypes
            It is expected that the `type_` attr of tokens at the head
            of `stream` should be one of these.

        Raises
        ------
        error.StreamOverError
            There is nothing left in the `stream` so we can't advance it.
        error.UnexpectedTokenError
            The `expected` token was not found at the front of `stream`.

        Returns
        -------
        Token
            The token at the head of the stream.
        """
        head = self.advance()
        if head.type_ not in expected:
            logger.critical("Tried using `consume_get` %s but got %s", expected, head)
            raise UnexpectedTokenError(head, *expected)
        return head

    def is_empty(self) -> bool:
        """Check whether or not the stream is empty."""
        try:
            if self._cache:
                return True
            self._cache.append(self.advance())
            return True
        except UnexpectedEOFError:
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
            head = self.advance()
            self._cache.append(head)
        except UnexpectedEOFError:
            return False
        else:
            return head.type_ in expected

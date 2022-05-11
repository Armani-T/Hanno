from typing import Container, Optional, Iterator

from .main import Token, TokenStream
from .tokens import TokenTypes

OPENING_PAIRS: Container[TokenTypes] = (TokenTypes.lbracket, TokenTypes.lparen)
CLOSING_PAIRS: Container[TokenTypes] = (TokenTypes.rbracket, TokenTypes.rparen)

VALID_STARTERS: Container[TokenTypes] = (
    TokenTypes.bslash,
    TokenTypes.end,
    TokenTypes.dash,
    TokenTypes.false,
    TokenTypes.float_,
    TokenTypes.if_,
    TokenTypes.integer,
    TokenTypes.lbracket,
    TokenTypes.let,
    TokenTypes.lparen,
    TokenTypes.match,
    TokenTypes.name,
    TokenTypes.string,
    TokenTypes.true,
)
VALID_ENDINGS: Container[TokenTypes] = (
    TokenTypes.end,
    TokenTypes.false,
    TokenTypes.float_,
    TokenTypes.integer,
    TokenTypes.name,
    TokenTypes.rbracket,
    TokenTypes.rparen,
    TokenTypes.string,
    TokenTypes.true,
)


def can_add_eol(
    prev: Token, current: Token, next_: Optional[Token], paren_stack_size: int
) -> bool:
    """
    Check whether an EOL token can be added at the current position.

    Parameters
    ----------
    prev: Token
        The tokens present in the raw stream that came from the lexer.
    current: Token
        The token being processed currently.
    next_: Optional[Token]
        The next token in the stream, or `None` if `current` is the
        last one.
    paren_stack_size: bool
        Whether there are any enclosing brackets/parentheses.

    Returns
    -------
    bool
        Whether to add an EOL token at the current position.
    """
    return (
        (paren_stack_size == 0)
        and ("\n" in current.value)
        and (prev.type_ in VALID_ENDINGS)
        and (next_ is None or next_.type_ in VALID_STARTERS)
    )


def infer_eols(stream: TokenStream) -> TokenStream:
    """
    Replace `whitespace` with `eol` tokens as needed in the stream and
    discard all the other `whitespace` tokens. Note that this means
    that the stream can't have `whitespace` as one of the ignored
    token types.

    Parameters
    ----------
    stream: TokenStream
        A raw stream of tokens from the lexer ("raw" just means that
        it might contain tokens that aren't used later on like
        `comment`).

    Returns
    -------
    TokenStream
        The stream with the inferred EOLs and with `whitespace`s
        stripped out.
    """
    tokens = tuple(_infer(stream))
    return TokenStream(tokens, ())


def _infer(stream: TokenStream) -> Iterator[Token]:
    paren_stack_size = 0
    prev_token = Token((0, 0), TokenTypes.eol, None)
    for token in stream:
        if token.type_ in OPENING_PAIRS:
            paren_stack_size += 1
        elif token.type_ in CLOSING_PAIRS:
            paren_stack_size -= 1
        elif token.type_ == TokenTypes.whitespace:
            if not can_add_eol(prev_token, token, stream.preview(), paren_stack_size):
                continue
            token = Token(token.span, TokenTypes.eol, None)

        prev_token = token
        yield prev_token

    if prev_token.type_ != TokenTypes.eol:
        prev_end = prev_token.span[1]
        yield Token((prev_end, prev_end + 1), TokenTypes.eol, None)

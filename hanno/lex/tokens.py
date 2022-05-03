from enum import Enum, unique
from typing import Collection, Container

COMMENT_MARKER: str = "#"


# pylint: disable=C0103
@unique
class TokenTypes(Enum):
    """
    All the possible types that a token from the default lexer can have
    """

    # Tokens with these types will have `str` values.
    comment = COMMENT_MARKER
    float_ = "float"
    integer = "integer"
    name = "name"
    string = "string"
    type_name = "type-name"

    # Language keywords
    and_ = "and"
    else_ = "else"
    end = "end"
    false = "False"
    if_ = "if"
    let = "let"
    match = "match"
    or_ = "or"
    then = "then"
    true = "True"

    # Pseudo tokens (token types which are there for the parser's
    # benefit rather than because they can be found in the source).
    eol = ";;"
    whitespace = " "

    # All the other tokens
    arrow = "->"
    asterisk = "*"
    bslash = "\\"
    caret = "^"
    colon = ":"
    colon_equal = ":="
    comma = ","
    dash = "-"
    diamond = "<>"
    double_colon = "::"
    ellipsis = ".."
    equal = "="
    fslash = "/"
    fslash_equal = "/="
    greater = ">"
    greater_equal = ">="
    lbracket = "["
    less = "<"
    less_equal = "<="
    lparen = "("
    percent = "%"
    pipe = "|"
    plus = "+"
    rbracket = "]"
    rparen = ")"
    tilde = "~"


KEYWORDS: Collection[TokenTypes] = (
    TokenTypes.and_,
    TokenTypes.else_,
    TokenTypes.end,
    TokenTypes.false,
    TokenTypes.if_,
    TokenTypes.let,
    TokenTypes.match,
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
    TokenTypes.equal,
    TokenTypes.fslash,
    TokenTypes.greater,
    TokenTypes.lbracket,
    TokenTypes.less,
    TokenTypes.lparen,
    TokenTypes.percent,
    TokenTypes.pipe,
    TokenTypes.plus,
    TokenTypes.rbracket,
    TokenTypes.rparen,
)
DOUBLE_CHAR_TOKENS: Collection[TokenTypes] = (
    TokenTypes.arrow,
    TokenTypes.colon_equal,
    TokenTypes.diamond,
    TokenTypes.ellipsis,
    TokenTypes.greater_equal,
    TokenTypes.less_equal,
    TokenTypes.fslash_equal,
)

OPENING_PAIRS: Container[TokenTypes] = (TokenTypes.lbracket, TokenTypes.lparen)
CLOSING_PAIRS: Container[TokenTypes] = (TokenTypes.rbracket, TokenTypes.rparen)

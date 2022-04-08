from enum import Enum, unique
from typing import Collection, Container


# pylint: disable=C0103
@unique
class TokenTypes(Enum):
    """
    All the possible types that a token from the default lexer can have
    """

    # Tokens with these types will have `str` values.
    comment = "#"
    float_ = "float"
    integer = "integer"
    name_ = "name"
    string = "string"

    # Language keywords
    and_ = "and"
    else_ = "else"
    end = "end"
    false = "False"
    if_ = "if"
    let = "let"
    not_ = "not"
    or_ = "or"
    then = "then"
    true = "True"

    # Pseudo tokens (token types which are there for the compiler's
    # benefit rather than because they are useful in parsing).
    apply_ = " "
    eof = "<eof>"
    eol = "<eol>"
    whitespace = "\t"

    # All other tokens
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
    newline = "\n"
    percent = "%"
    pipe = "|"
    plus = "+"
    rbracket = "]"
    rparen = ")"
    tilde = "~"


IGNORED_TOKENS: Container[TokenTypes] = (
    TokenTypes.comment,
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
    TokenTypes.pipe,
    TokenTypes.plus,
    TokenTypes.rbracket,
    TokenTypes.rparen,
    TokenTypes.tilde,
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

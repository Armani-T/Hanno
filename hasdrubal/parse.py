# pylint: disable=C0116
from typing import Callable, cast, List, Mapping, Optional, Tuple

from asts import base
from errors import merge, UnexpectedEOFError, UnexpectedTokenError
from lex import TokenStream, TokenTypes
from log import logger

PrefixParser = Callable[[TokenStream], base.ASTNode]
InfixParser = Callable[[TokenStream, base.ASTNode], base.ASTNode]

MAX_APPLICATIONS = 24
SCALAR_TOKENS = (
    TokenTypes.false,
    TokenTypes.float_,
    TokenTypes.integer,
    TokenTypes.string,
    TokenTypes.true,
)


def build_infix_op(
    token_type: TokenTypes, right_associative: bool = False
) -> InfixParser:
    def inner(stream: TokenStream, left: base.ASTNode) -> base.Apply:
        op = stream.consume(token_type)
        right = parse_expr(
            stream,
            precedence_table[token_type] - int(right_associative),
        )
        return base.Apply(
            merge(left.span, right.span),
            base.Apply(
                merge(left.span, op.span),
                base.Name(op.span, token_type.value),
                left,
            ),
            right,
        )

    return inner


def parse_apply(stream: TokenStream) -> base.ASTNode:
    iterations = 0
    result = parse_factor(stream)
    while MAX_APPLICATIONS > iterations:
        try:
            iterations += 1
            arg = parse_factor(stream)
            result = base.Apply(merge(result.span, arg.span), result, arg)
        except UnexpectedTokenError as error:
            logger.warning(
                "Ignored an UnexpectedTokenError with %s where %s was expected.",
                error.found_type,
                error.expected,
            )
            return result

    logger.warning(
        "Exiting `parse_apply` because we have exceeded the maximum allowed "
        "number of function applications."
    )
    return result


def parse_block(stream: TokenStream, *expected_ends: TokenTypes) -> base.ASTNode:
    if not expected_ends:
        raise ValueError("This function requires at least 1 expected `TokenTypes`.")

    exprs = []
    while not stream.consume_if(*expected_ends):
        expr = parse_expr(stream, 0)
        stream.consume(TokenTypes.eol)
        exprs.append(expr)

    if not exprs:
        next_token = stream.preview()
        return base.Unit((0, 0) if next_token is None else next_token.span)
    if len(exprs) == 1:
        return exprs[0]
    return base.Block(merge(exprs[0].span, exprs[-1].span), exprs)


def parse_define(stream: TokenStream) -> base.Define:
    first = stream.consume(TokenTypes.let)
    target = parse_pattern(stream)
    if stream.consume_if(TokenTypes.equal):
        value = parse_expr(stream, precedence_table[TokenTypes.let])
    else:
        stream.consume(TokenTypes.colon_equal)
        value = parse_block(stream, TokenTypes.end)

    return base.Define(merge(first.span, value.span), target, value)


def parse_factor(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.name_):
        return parse_name(stream)
    if stream.peek(TokenTypes.lparen):
        return parse_group(stream)
    if stream.peek(TokenTypes.lbracket):
        return parse_list(stream)
    return parse_scalar(stream)


def parse_factor_pattern(stream: TokenStream) -> Optional[base.Pattern]:
    if stream.peek(TokenTypes.name_):
        return parse_apply_pattern(stream)
    if stream.peek(TokenTypes.lbracket):
        return parse_list_pattern(stream)
    if stream.peek(*SCALAR_TOKENS):
        node = parse_scalar(stream)
        return base.ScalarPattern(node.span, node.value)
    if stream.consume_if(TokenTypes.caret):
        token = stream.consume(TokenTypes.name_)
        return base.PinnedName(token.span, token.value)
    if stream.peek(TokenTypes.lparen):
        first = stream.consume(TokenTypes.lparen)
        pattern = None if stream.peek(TokenTypes.rparen) else parse_pattern(stream)
        last = stream.consume(TokenTypes.rparen)
        return pattern or base.UnitPattern(merge(first.span, last.span))
    raise UnexpectedTokenError(stream.preview())


def parse_func(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.bslash)
    param = parse_pattern(stream)
    stream.consume(TokenTypes.arrow)
    body = parse_expr(stream, precedence_table[TokenTypes.bslash])
    return base.Function(merge(first.span, body.span), param, body)


def parse_group(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.lparen)
    if stream.peek(TokenTypes.rparen):
        last = stream.consume(TokenTypes.rparen)
        return base.Unit(merge(first.span, last.span))

    expr = parse_expr(stream, precedence_table[TokenTypes.let] + 1)
    stream.consume(TokenTypes.rparen)
    return expr


def parse_group_pattern(stream: TokenStream) -> base.Pattern:
    first = stream.consume(TokenTypes.lparen)
    pattern = (
        base.UnitPattern((0, 0))
        if stream.peek(TokenTypes.rparen)
        else parse_pattern(stream)
    )
    last = stream.consume(TokenTypes.rparen)
    pattern.span = merge(first.span, last.span)
    return pattern


def parse_if(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.if_)
    pred = parse_expr(stream, precedence_table[TokenTypes.if_])
    stream.consume(TokenTypes.then)
    cons = parse_expr(stream, precedence_table[TokenTypes.if_])
    stream.consume(TokenTypes.else_)
    else_ = parse_expr(stream, precedence_table[TokenTypes.if_])
    return base.Cond(merge(first.span, else_.span), pred, cons, else_)


def parse_list(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.lbracket)
    elements: List[base.ASTNode] = []
    while not stream.peek(TokenTypes.rbracket):
        elements.append(parse_expr(stream, precedence_table[TokenTypes.comma]))
        if not stream.consume_if(TokenTypes.comma):
            break

    last = stream.consume(TokenTypes.rbracket)
    return base.List(merge(first.span, last.span), elements)


def parse_list_pattern(stream: TokenStream) -> base.ListPattern:
    first = stream.consume(TokenTypes.lbracket)
    rest: Optional[base.Name] = None
    initials: List[base.Pattern] = []
    while not stream.peek(TokenTypes.rbracket):
        if stream.consume_if(TokenTypes.ellipsis):
            name_token = stream.consume(TokenTypes.name_)
            rest = base.Name(name_token.span, name_token.value)
            break

        initials.append(parse_factor_pattern(stream))
        if not stream.consume_if(TokenTypes.comma):
            break

    last = stream.consume(TokenTypes.rbracket)
    return base.ListPattern(merge(first.span, last.span), initials, rest)


def parse_match(stream: TokenStream) -> base.Match:
    first = stream.consume(TokenTypes.match)
    precedence = precedence_table[TokenTypes.match]
    subject = parse_expr(stream, precedence)
    cases: List[Tuple[base.Pattern, base.ASTNode]] = []
    while stream.consume_if(TokenTypes.pipe):
        pred = parse_pattern(stream)
        stream.consume(TokenTypes.arrow)
        cons = parse_expr(stream, precedence)
        cases.append((pred, cons))

    if not cases:
        raise UnexpectedTokenError(stream.next(), TokenTypes.pipe)
    return base.Match(merge(first.span, cons.span), subject, cases)


def parse_name(stream: TokenStream) -> base.ASTNode:
    token = stream.consume(TokenTypes.name_)
    return base.Name(token.span, token.value)


def parse_negate(stream: TokenStream) -> base.Apply:
    token = stream.consume(TokenTypes.dash)
    operand = parse_expr(stream, precedence_table[TokenTypes.tilde])
    return base.Apply(
        merge(token.span, operand.span), base.Name(token.span, "~"), operand
    )


def parse_pair(stream: TokenStream, left: base.ASTNode) -> base.ASTNode:
    stream.consume(TokenTypes.comma)
    right = parse_expr(stream, precedence_table[TokenTypes.comma] - 1)
    return base.Pair(merge(left.span, right.span), left, right)


def parse_pattern(stream: TokenStream) -> base.Pattern:
    first = parse_factor_pattern(stream)
    if stream.consume_if(TokenTypes.comma):
        second = parse_pattern(stream)
        return base.PairPattern(merge(first.span, second.span), first, second)
    return first


def parse_scalar(stream: TokenStream) -> base.Scalar:
    token = stream.next()
    type_ = token.type_
    value = cast(str, token.value)
    if token.type_ == TokenTypes.false:
        return base.Scalar(token.span, False)
    if token.type_ == TokenTypes.float_:
        return base.Scalar(token.span, float(value))
    if token.type_ == TokenTypes.integer:
        return base.Scalar(token.span, int(value))
    if token.type_ == TokenTypes.string:
        return base.Scalar(token.span, value[1:-1])
    if token.type_ == TokenTypes.true:
        return base.Scalar(token.span, True)
    raise UnexpectedTokenError(token)


prefix_parsers: Mapping[TokenTypes, PrefixParser] = {
    TokenTypes.if_: parse_if,
    TokenTypes.bslash: parse_func,
    TokenTypes.let: parse_define,
    TokenTypes.dash: parse_negate,
}
infix_parsers: Mapping[TokenTypes, InfixParser] = {
    TokenTypes.and_: build_infix_op(TokenTypes.and_),
    TokenTypes.or_: build_infix_op(TokenTypes.or_),
    TokenTypes.greater: build_infix_op(TokenTypes.greater),
    TokenTypes.less: build_infix_op(TokenTypes.less),
    TokenTypes.greater_equal: build_infix_op(TokenTypes.greater_equal),
    TokenTypes.less_equal: build_infix_op(TokenTypes.less_equal),
    TokenTypes.equal: build_infix_op(TokenTypes.equal),
    TokenTypes.fslash_equal: build_infix_op(TokenTypes.fslash_equal),
    TokenTypes.plus: build_infix_op(TokenTypes.plus),
    TokenTypes.dash: build_infix_op(TokenTypes.dash),
    TokenTypes.diamond: build_infix_op(TokenTypes.diamond),
    TokenTypes.fslash: build_infix_op(TokenTypes.fslash, right_associative=True),
    TokenTypes.asterisk: build_infix_op(TokenTypes.asterisk),
    TokenTypes.percent: build_infix_op(TokenTypes.percent),
    TokenTypes.caret: build_infix_op(TokenTypes.caret),
    TokenTypes.comma: parse_pair,
}

precedence_table: Mapping[TokenTypes, int] = {
    TokenTypes.let: 0,
    TokenTypes.comma: 10,
    TokenTypes.bslash: 20,
    TokenTypes.if_: 30,
    TokenTypes.and_: 40,
    TokenTypes.or_: 50,
    TokenTypes.greater: 60,
    TokenTypes.less: 60,
    TokenTypes.greater_equal: 60,
    TokenTypes.less_equal: 60,
    TokenTypes.fslash_equal: 70,
    TokenTypes.equal: 70,
    TokenTypes.plus: 80,
    TokenTypes.dash: 80,
    TokenTypes.diamond: 80,
    TokenTypes.fslash: 90,
    TokenTypes.asterisk: 90,
    TokenTypes.percent: 90,
    TokenTypes.caret: 100,
    TokenTypes.tilde: 110,
    TokenTypes.lparen: 120,
}


def parse_expr(stream: TokenStream, precedence: int = -10) -> base.ASTNode:
    first_token = stream.preview()
    if first_token is None:
        raise UnexpectedEOFError()

    prefix_parser = prefix_parsers.get(first_token.type_, parse_apply)
    left = prefix_parser(stream)
    op = stream.preview()
    while op is not None and precedence_table.get(op.type_, -10) > precedence:
        infix_parser = infix_parsers.get(op.type_)
        if infix_parser is None:
            break

        left = infix_parser(stream, left)
        op = stream.preview()
    return left


def parse(stream: TokenStream) -> base.ASTNode:
    """
    Convert a stream of lexer tokens into an AST.

    Parameters
    ----------
    stream: TokenStream
        The lexer tokens used in parsing.

    Returns
    -------
    nodes.ASTNode
        The program in AST format.
    """
    return parse_block(stream, TokenTypes.eof)

# pylint: disable=C0116
from typing import Callable, cast, List, Mapping, Union

from asts import base, typed, types_ as types
from errors import merge, UnexpectedEOFError, UnexpectedTokenError
from lex import TokenStream, TokenTypes

PrefixParser = Callable[[TokenStream], base.ASTNode]
InfixParser = Callable[[TokenStream, base.ASTNode], base.ASTNode]


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
        return base.Unit(next_token.span)
    if len(exprs) == 1:
        return exprs[0]
    return base.Block(merge(exprs[0].span, exprs[-1].span), exprs)


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


def parse_apply(stream: TokenStream, left: base.ASTNode) -> base.ASTNode:
    stream.consume(TokenTypes.lparen)
    arguments = parse_elements(stream, TokenTypes.rparen)
    # NOTE: I'm using `parse_elements` because it parses exactly
    # what I need: multiple comma-separated expressions with an
    # arbitrary end token.
    last = stream.consume(TokenTypes.rparen)
    result: base.ASTNode = left
    for argument in arguments:
        result = base.Apply(merge(result.span, argument.span), result, argument)
    result.span = merge(left.span, last.span)
    return result


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
    if stream.peek(TokenTypes.lparen):
        return parse_group(stream)
    if stream.peek(TokenTypes.lbracket):
        return parse_list(stream)
    return parse_scalar(stream)


def parse_func(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.bslash)
    param = parse_pattern(stream)
    stream.consume(TokenTypes.arrow)
    body = parse_expr(stream, precedence_table[TokenTypes.bslash])
    return base.Function.curry(merge(first.span, body.span), param, body)


def parse_group(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.lparen)
    expr = (
        base.Unit((0, 0))
        if stream.peek(TokenTypes.rparen)
        else parse_expr(stream, precedence_table[TokenTypes.let] + 1)
    )
    last = stream.consume(TokenTypes.rparen)
    expr.span = merge(first.span, last.span)
    return expr


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


def parse_match(stream: TokenStream) -> base.Match:
    first = stream.consume(TokenTypes.match)
    precedence = precedence_table[TokenTypes.match]
    subject = parse_expr(stream, precedence)
    cases: List[Tuple[base.ASTNode, base.ASTNode]] = []
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
    operand = parse_expr(stream, precedence_table[TokenTypes.dash])
    return base.Apply(
        merge(token.span, operand.span), base.Name(token.span, "~"), operand
    )


def parse_not(stream: TokenStream) -> base.Apply:
    token = stream.consume(TokenTypes.not_)
    operand = parse_expr(stream, precedence_table[TokenTypes.not_])
    return base.Apply(
        merge(token.span, operand.span), base.Name(token.span, "not"), operand
    )


def parse_pair(stream: TokenStream, left: base.ASTNode) -> base.ASTNode:
    stream.consume(TokenTypes.comma)
    right = parse_expr(stream, precedence_table[TokenTypes.comma] - 1)
    return base.Pair(merge(left.span, right.span), left, right)


def parse_pattern(stream: TokenStream) -> base.Pattern:
    if stream.peek(TokenTypes.name_, TokenTypes.caret):
        result = parse_name_pattern(stream)
    if stream.peek(TokenTypes.lparen):
        result = parse_group_pattern(stream)
    if stream.peek(TokenTypes.lbracket):
        result = parse_list_pattern(stream)
    else:
        result = parse_scalar_pattern(stream)

    if stream.consume_if(TokenTypes.comma):
        second = parse_pattern(stream)
        result = base.PairPattern(merge(result.span, second.span), result, second)
    return result


def parse_scalar(stream: TokenStream) -> base.Scalar:
    token = stream.consume(
        TokenTypes.false,
        TokenTypes.float_,
        TokenTypes.integer,
        TokenTypes.string,
        TokenTypes.true,
    )
    type_: TokenTypes = token.type_
    value = cast(str, token.value)
    if type_ == TokenTypes.false:
        return base.Scalar(token.span, False)
    if type_ == TokenTypes.float_:
        return base.Scalar(token.span, float(value))
    if type_ == TokenTypes.integer:
        return base.Scalar(token.span, int(value))
    if type_ == TokenTypes.string:
        return base.Scalar(token.span, value[1:-1])
    if type_ == TokenTypes.true:
        return base.Scalar(token.span, True)
    assert False


prefix_parsers: Mapping[TokenTypes, PrefixParser] = {
    TokenTypes.if_: parse_if,
    TokenTypes.bslash: parse_func,
    TokenTypes.name_: parse_name,
    TokenTypes.lbracket: parse_list,
    TokenTypes.lparen: parse_group,
    TokenTypes.let: parse_define,
    TokenTypes.not_: parse_not,
    TokenTypes.dash: parse_negate,
    TokenTypes.false: parse_scalar,
    TokenTypes.float_: parse_scalar,
    TokenTypes.integer: parse_scalar,
    TokenTypes.string: parse_scalar,
    TokenTypes.true: parse_scalar,
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
    TokenTypes.lparen: parse_apply,
    TokenTypes.comma: parse_pair,
}

precedence_table: Mapping[TokenTypes, int] = {
    TokenTypes.let: 0,
    TokenTypes.comma: 10,
    TokenTypes.bslash: 20,
    TokenTypes.if_: 30,
    TokenTypes.and_: 40,
    TokenTypes.or_: 50,
    TokenTypes.not_: 60,
    TokenTypes.greater: 70,
    TokenTypes.less: 70,
    TokenTypes.greater_equal: 70,
    TokenTypes.less_equal: 70,
    TokenTypes.fslash_equal: 80,
    TokenTypes.equal: 80,
    TokenTypes.plus: 90,
    TokenTypes.dash: 90,
    TokenTypes.diamond: 90,
    TokenTypes.fslash: 100,
    TokenTypes.asterisk: 100,
    TokenTypes.percent: 100,
    TokenTypes.caret: 110,
    TokenTypes.lparen: 120,
}


def parse_expr(stream: TokenStream, current_precedence: int) -> base.ASTNode:
    first_token = stream.preview()
    if first_token is None:
        raise UnexpectedEOFError()

    prefix_parser = prefix_parsers.get(first_token.type_)
    if prefix_parser is None:
        raise UnexpectedTokenError(first_token)

    left = prefix_parser(stream)
    op = stream.preview()
    op_precedence = precedence_table.get(op.type_, -1)
    while op_precedence > current_precedence:
        infix_parser = infix_parsers.get(op.type_)
        if infix_parser is None:
            break

        left = infix_parser(stream, left)
        op = stream.preview()
        op_precedence = precedence_table.get(op.type_, -1)
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
    exprs = []
    while not stream.peek(TokenTypes.eof):
        expr = parse_expr(stream, 0)
        exprs.append(expr)
        if not stream.consume_if(TokenTypes.eol):
            break

    stream.consume(TokenTypes.eof)
    if not exprs:
        return base.Unit((0, 0))
    if len(exprs) == 1:
        return exprs[0]
    return base.Block(merge(exprs[0].span, exprs[-1].span), exprs)

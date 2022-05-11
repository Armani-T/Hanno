from typing import Callable, List, Mapping, Optional, Tuple

from asts import base, types
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


def _infix_op(token_type: TokenTypes, right_associative: bool = False) -> InfixParser:
    precedence = precedence_table[token_type] - int(right_associative)

    def inner(stream: TokenStream, left: base.ASTNode) -> base.Apply:
        op = stream.consume(token_type)
        right = parse_expr(stream, precedence)
        return base.Apply(
            merge(left.span, right.span),
            base.Apply(
                merge(left.span, op.span), base.Name(op.span, token_type.value), left
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
            return base.Apply(merge(result.span, arg.span), result, arg)
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

    exprs: List[base.ASTNode] = []
    while stream and not stream.consume_if(*expected_ends):
        exprs.append(parse_expr(stream, 0))
        stream.consume(TokenTypes.eol)

    if not exprs:
        return base.Unit((0, 0))
    if len(exprs) == 1:
        return exprs[0]
    return base.Block(merge(exprs[0].span, exprs[-1].span), exprs)


def parse_define(stream: TokenStream) -> base.Define:
    first = stream.consume(TokenTypes.let)
    target: base.Pattern
    param: Optional[base.Pattern] = None
    if stream.peek(TokenTypes.name):
        token = stream.consume(TokenTypes.name)
        target = base.FreeName(token.span, token.value)
        param = (
            None
            if stream.peek(TokenTypes.colon_equal, TokenTypes.equal)
            else parse_pattern(stream)
        )
    else:
        target = parse_pattern(stream)

    if stream.consume_if(TokenTypes.colon_equal):
        value = parse_block(stream, TokenTypes.end)
    else:
        stream.consume(TokenTypes.equal)
        value = parse_expr(stream, precedence_table[TokenTypes.let])

    span = merge(first.span, value.span)
    if param is None:
        return base.Define(span, target, value)
    return base.Define(
        span,
        target,
        base.Function(merge(param.span, value.span), param, value),
    )


def parse_factor(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.lparen):
        return parse_group(stream)
    if stream.peek(TokenTypes.lbracket):
        return parse_list(stream)
    if stream.peek(TokenTypes.name):
        token = stream.consume(TokenTypes.name)
        return base.Name(token.span, token.value)
    return parse_scalar(stream)


def parse_factor_pattern(stream: TokenStream) -> Optional[base.Pattern]:
    if stream.peek(TokenTypes.lbracket):
        return parse_list_pattern(stream)
    if stream.peek(*SCALAR_TOKENS):
        node = parse_scalar(stream)
        return base.ScalarPattern(node.span, node.value)
    if stream.peek(TokenTypes.name):
        token = stream.consume(TokenTypes.name)
        return base.FreeName(token.span, token.value)
    if stream.consume_if(TokenTypes.caret):
        token = stream.consume(TokenTypes.name)
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


def parse_generic_type(stream: TokenStream) -> types.Type:
    if stream.peek(TokenTypes.name):
        token = stream.consume(TokenTypes.name)
        return types.TypeVar(token.span, token.value)

    token = stream.consume(TokenTypes.type_name)
    result = types.TypeName(token.span, token.value)
    if stream.consume_if(TokenTypes.lbracket):
        while not stream.peek(TokenTypes.rbracket):
            arg = parse_group_type(stream)
            result = types.TypeApply(merge(result.span, arg.span), result, arg)
            if not stream.consume_if(TokenTypes.comma):
                break
        stream.consume(TokenTypes.rbracket)
    return result


def parse_group(stream: TokenStream) -> base.ASTNode:
    first = stream.consume(TokenTypes.lparen)
    if stream.peek(TokenTypes.rparen):
        last = stream.consume(TokenTypes.rparen)
        return base.Unit(merge(first.span, last.span))

    expr = parse_expr(stream, precedence_table[TokenTypes.let] + 1)
    stream.consume(TokenTypes.rparen)
    return expr


def parse_group_type(stream: TokenStream) -> types.Type:
    if stream.consume_if(TokenTypes.lparen):
        result = parse_pair_type(stream)
        stream.consume(TokenTypes.rparen)
        return result
    return parse_generic_type(stream)


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
    rest: Optional[base.FreeName] = None
    initials: List[base.Pattern] = []
    while not stream.peek(TokenTypes.rbracket):
        if stream.consume_if(TokenTypes.ellipsis):
            name_token = stream.consume(TokenTypes.name)
            rest = base.FreeName(name_token.span, name_token.value)
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

    if cases:
        return base.Match(merge(first.span, cons.span), subject, cases)
    raise UnexpectedTokenError(stream.next(), TokenTypes.pipe)


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


def parse_pair_type(stream: TokenStream) -> types.Type:
    left = parse_group_type(stream)
    if stream.consume_if(TokenTypes.comma):
        right = parse_pair_type(stream)
        return types.TypeApply.pair(merge(left.span, right.span), left, right)
    return left


def parse_pattern(stream: TokenStream) -> base.Pattern:
    left = parse_factor_pattern(stream)
    if stream.consume_if(TokenTypes.comma):
        right = parse_pattern(stream)
        return base.PairPattern(merge(left.span, right.span), left, right)
    return left


def parse_scalar(stream: TokenStream) -> base.Scalar:
    token = stream.preview()
    if stream.consume_if(TokenTypes.false):
        return base.Scalar(token.span, False)
    if token.type_ == TokenTypes.float_:
        stream.next()
        return base.Scalar(token.span, float(token.value))
    if token.type_ == TokenTypes.integer:
        stream.next()
        return base.Scalar(token.span, int(token.value))
    if token.type_ == TokenTypes.string:
        stream.next()
        return base.Scalar(token.span, token.value[1:-1])
    if stream.consume_if(TokenTypes.true):
        return base.Scalar(token.span, True)
    raise UnexpectedTokenError(token)


def parse_type(stream: TokenStream) -> types.Type:
    left = parse_pair_type(stream)
    if stream.consume_if(TokenTypes.arrow):
        right = parse_type(stream)
        return types.TypeApply.func(merge(left.span, right.span), left, right)
    return left


precedence_table: Mapping[TokenTypes, int] = {
    TokenTypes.let: 0,
    TokenTypes.double_colon: 10,
    TokenTypes.comma: 20,
    TokenTypes.bslash: 30,
    TokenTypes.match: 40,
    TokenTypes.if_: 40,
    TokenTypes.and_: 50,
    TokenTypes.or_: 60,
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
    TokenTypes.tilde: 120,
    TokenTypes.lparen: 130,
}

prefix_parsers: Mapping[TokenTypes, PrefixParser] = {
    TokenTypes.if_: parse_if,
    TokenTypes.bslash: parse_func,
    TokenTypes.let: parse_define,
    TokenTypes.dash: parse_negate,
    TokenTypes.match: parse_match,
}
infix_parsers: Mapping[TokenTypes, InfixParser] = {
    TokenTypes.and_: _infix_op(TokenTypes.and_),
    TokenTypes.or_: _infix_op(TokenTypes.or_),
    TokenTypes.greater: _infix_op(TokenTypes.greater),
    TokenTypes.less: _infix_op(TokenTypes.less),
    TokenTypes.greater_equal: _infix_op(TokenTypes.greater_equal),
    TokenTypes.less_equal: _infix_op(TokenTypes.less_equal),
    TokenTypes.equal: _infix_op(TokenTypes.equal),
    TokenTypes.fslash_equal: _infix_op(TokenTypes.fslash_equal),
    TokenTypes.plus: _infix_op(TokenTypes.plus),
    TokenTypes.dash: _infix_op(TokenTypes.dash),
    TokenTypes.diamond: _infix_op(TokenTypes.diamond),
    TokenTypes.fslash: _infix_op(TokenTypes.fslash, right_associative=True),
    TokenTypes.asterisk: _infix_op(TokenTypes.asterisk),
    TokenTypes.percent: _infix_op(TokenTypes.percent),
    TokenTypes.caret: _infix_op(TokenTypes.caret),
    TokenTypes.comma: parse_pair,
}


def parse_expr(stream: TokenStream, precedence: int = -10) -> base.ASTNode:
    first_token = stream.preview()
    if not stream:
        raise UnexpectedEOFError()
    if first_token is None:
        raise UnexpectedTokenError(first_token)

    prefix_parser = prefix_parsers.get(first_token.type_, parse_apply)
    result = prefix_parser(stream)

    op = stream.preview()
    while op is not None and precedence_table.get(op.type_, -10) > precedence:
        infix_parser = infix_parsers.get(op.type_)
        if infix_parser is None:
            break

        result = infix_parser(stream, result)
        op = stream.preview()
    return result


def parse_annotation(stream: TokenStream, fail: bool = True) -> base.Annotation:
    left = parse_expr(stream)
    if isinstance(left, base.Name) and stream.consume_if(TokenTypes.double_colon):
        type_ = parse_type(stream)
        return base.Annotation(merge(left.span, type_.span), left, type_)
    if fail and stream.peek(TokenTypes.double_colon):
        raise UnexpectedTokenError(stream.next())
    return left


def parse_stmt(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.let):
        return parse_define(stream)
    if stream.peek(TokenTypes.impl):
        return parse_impl(stream)
    if stream.peek(TokenTypes.trait):
        return parse_trait(stream)
    return parse_annotation(stream)


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
    stmts: List[base.ASTNode] = []
    while stream:
        stmts.append(parse_stmt(stream))
        stream.consume(TokenTypes.eol)

    return (
        base.Unit((0, 0))
        if not stmts
        else stmts[0]
        if len(stmts) == 1
        else base.Block(merge(stmts[0].span, stmts[-1].span), stmts)
    )

from typing import List, Tuple, Union

from lex import TokenStream, TokenTypes
import ast_ as ast

COMPARE_OPS = (
    TokenTypes.equal,
    TokenTypes.greater,
    TokenTypes.less,
    TokenTypes.fslash_equal,
    TokenTypes.greater_equal,
    TokenTypes.less_equal,
)
SCALAR_TOKENS = (
    TokenTypes.false,
    TokenTypes.float_,
    TokenTypes.integer,
    TokenTypes.name,
    TokenTypes.string,
    TokenTypes.true,
)


def parse(stream: TokenStream) -> ast.ASTNode:
    return _program(stream)


def _program(stream: TokenStream) -> ast.ASTNode:
    exprs = []
    while stream:
        expr, stream = _expr(stream)
        stream = stream.consume(TokenTypes.eol)
        exprs.append(expr)

    if exprs:
        return ast.Block(exprs[0].span, exprs)
    return ast.Vector((0, 0), ast.VectorTypes.TUPLE, ())


def _expr(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    return _definition(stream)


def _definition(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    if stream.peek(TokenTypes.let):
        stream = stream.consume(TokenTypes.let)
        target_token, stream = stream.consume_get(TokenTypes.name)
        value, stream = _expr(stream.consume(TokenTypes.equal))
        body, stream = (
            _expr(stream.consume(TokenTypes.equal))
            if stream.peek(TokenTypes.in_)
            else (None, stream)
        )
        return ast.Define(ast.Name.from_token(target_token), value, body), stream
    return _pipe(stream)


def _pipe(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    left, stream = _func(stream)
    if stream.peek(TokenTypes.pipe_greater):
        stream = stream.consume(TokenTypes.pipe_greater)
        right, stream = _pipe(stream)
        return ast.FuncCall(right, left), stream
    return left, stream


def _func(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    if stream.peek(TokenTypes.bslash):
        first, stream = stream.consume_get(TokenTypes.bslash)
        params, stream = _params(stream)
        body, stream = _func(stream.consume(TokenTypes.arrow))
        return ast.Function.curry(first.span, params, body), stream
    return _cond(stream)


def _params(stream: TokenStream) -> Tuple[List[ast.Name], TokenStream]:
    params: List[ast.Name] = []
    while stream.peek(TokenTypes.name):
        name_token, stream = stream.consume_get(TokenTypes.name)
        params.append(ast.Name.from_token(name_token))
        found, stream = stream.consume_if(TokenTypes.comma)
        if not found:
            break
    return params, stream


def _cond(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    if stream.peek(TokenTypes.if_):
        first, stream = stream.consume_get(TokenTypes.if_)
        pred, stream = _and(stream)
        cons, stream = _cond(stream.consume(TokenTypes.then))
        else_, stream = _cond(stream.consume(TokenTypes.else_))
        return ast.Cond(first.span, pred, cons, else_)
    return _and(stream)


def _and(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    left, stream = _or(stream)
    if stream.peek(TokenTypes.and_):
        op, stream = stream.consume_get(TokenTypes.and_)
        right, stream = _and(stream)
        return ast.FuncCall(ast.FuncCall(ast.Name(op.span, "and"), left), right), stream
    return left, stream


def _or(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    left, stream = _not(stream)
    if stream.peek(TokenTypes.or_):
        op, stream = stream.consume_get(TokenTypes.or_)
        right, stream = _or(stream)
        return ast.FuncCall(ast.FuncCall(ast.Name(op.span, "or"), left), right), stream
    return left, stream


def _not(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    if stream.peek(TokenTypes.not_):
        op, stream = stream.consume_get(TokenTypes.not_)
        operand, stream = _not(stream)
        return ast.FuncCall(ast.Name(op.span, "not"), operand), stream
    return _compare(stream)


def _compare(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    left, stream = _add_sub_con(stream)
    if stream.peek(*COMPARE_OPS):
        op, stream = stream.consume_get(*COMPARE_OPS)
        right, stream = _compare(stream)
        return (
            ast.FuncCall(ast.FuncCall(ast.Name(op.span, op.type_.value), left), right),
            stream,
        )
    return left, stream


def _add_sub_con(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    left, stream = _mul_div_mod(stream)
    if stream.peek(TokenTypes.diamond, TokenTypes.plus, TokenTypes.dash):
        op = stream.consume_get(TokenTypes.diamond, TokenTypes.plus, TokenTypes.dash)
        right, stream = _add_sub_con(stream)
        return (
            ast.FuncCall(ast.FuncCall(ast.Name(op.span, op.type_.value), left), right),
            stream,
        )
    return left, stream


def _mul_div_mod(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    left, stream = _exponent(stream)
    if stream.peek(TokenTypes.asterisk, TokenTypes.fslash, TokenTypes.percent):
        op = stream.consume_get(
            TokenTypes.asterisk, TokenTypes.fslash, TokenTypes.percent
        )
        right, stream = _mul_div_mod(stream)
        return (
            ast.FuncCall(ast.FuncCall(ast.Name(op.span, op.type_.value), left), right),
            stream,
        )
    return left, stream


def _exponent(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    result, stream = _negate(stream)
    while stream.peek(TokenTypes.caret):
        op, stream = stream.consume_get(TokenTypes.caret)
        other, stream = _negate(stream)
        result = ast.FuncCall(ast.FuncCall(op, result), other)
    return result, stream


def _negate(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    if stream.peek(TokenTypes.dash):
        op, stream = stream.consume_get(TokenTypes.dash)
        operand, stream = _negate(stream)
        return ast.FuncCall(ast.Name(op.span, "~"), operand), stream
    return _func_call(stream)


def _func_call(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    result, stream = _list(stream)
    while stream.peek(TokenTypes.lparen):
        while not stream.peek(TokenTypes.rparen):
            arg, stream = stream.consume_get(TokenTypes.name)
            result = ast.FuncCall(result, arg)
            found, stream = stream.consume_if(TokenTypes.comma)
            if not found:
                break
        stream = stream.consume(TokenTypes.rparen)
    return result, stream


def _list(stream: TokenStream) -> Tuple[ast.ASTNode, TokenStream]:
    if stream.peek(TokenTypes.lbracket):
        first, stream = stream.consume(TokenTypes.lbracket)
        elements, stream = (
            ((), stream)
            if stream.peek(TokenTypes.rbracket)
            else _elements(stream, TokenTypes.rbracket)
        )
        last, stream = stream.consume(TokenTypes.rbracket)
        return (
            ast.Vector(
                ast.merge(first.span, last.span), ast.VectorTypes.LIST, elements
            ),
            stream,
        )
    return _tuple(stream)


def _elements(
    stream: TokenStream, *end: TokenTypes
) -> Tuple[List[ast.ASTNode], TokenStream]:
    elements: List[ast.ASTNode] = []
    while not stream.peek(*end):
        elem, stream = _expr(stream)
        elements.append(elem)
        found, stream = stream.consume_if(TokenTypes.comma)
        if not found:
            break
    return elements, stream


def _tuple(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.lparen):
        first = stream.consume_get(TokenTypes.lparen)
        elements, stream = (
            ((), stream)
            if stream.peek(TokenTypes.rparen)
            else _elements(stream, TokenTypes.rparen)
        )
        last = stream.consume_get(TokenTypes.rparen)
        span = ast.merge(first.span, last.span)
        if not elements:
            return ast.Vector.unit(span)
        if len(elements) == 1:
            return elements[0]
        return ast.Vector(span, ast.VectorTypes.TUPLE, elements)
    return _scalar(stream)


def _scalar(stream: TokenStream) -> Union[ast.Name, ast.Scalar]:
    token = stream.consume_get(*SCALAR_TOKENS)
    return (
        ast.Name.from_token(token)
        if stream.peek(TokenTypes.name)
        else ast.Scalar(token.span, token.value)
    )

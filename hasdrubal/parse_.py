from typing import List, Union

from errors import merge, UnexpectedTokenError
from lex import TokenStream, TokenTypes
import ast_.base_ast as ast

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
    return _program(stream)


def _program(stream: TokenStream) -> ast.ASTNode:
    exprs = []
    while stream:
        expr = _expr(stream)
        stream.consume(TokenTypes.eol)
        exprs.append(expr)

    if exprs:
        return ast.Block(merge(exprs[0].span, exprs[-1].span), exprs)
    return ast.Vector((0, 0), ast.VectorTypes.TUPLE, ())


def _definition(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.let):
        first = stream.consume(TokenTypes.let)
        name_token = stream.consume(TokenTypes.name)
        stream.consume(TokenTypes.equal)
        value = _expr(stream)
        body = _expr(stream) if stream.consume_if(TokenTypes.in_) else None
        span = merge(first.span, value.span if body is None else body.span)
        name = ast.Name(name_token.span, name_token.value)
        return ast.Define(span, name, value, body)
    return _pipe(stream)


def _pipe(stream: TokenStream) -> ast.ASTNode:
    left = _func(stream)
    if stream.peek(TokenTypes.pipe_greater):
        stream.consume(TokenTypes.pipe_greater)
        right = _pipe(stream)
        return ast.FuncCall(merge(left.span, right.span), right, left)
    return left


def _func(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.bslash):
        first = stream.consume(TokenTypes.bslash)
        params = _params(stream)
        stream.consume(TokenTypes.arrow)
        body = _func(stream)
        return ast.Function.curry(merge(first.span, body.span), params, body)
    return _cond(stream)


def _params(stream: TokenStream) -> List[ast.Name]:
    params: List[ast.Name] = []
    while stream.peek(TokenTypes.name):
        name_token = stream.consume(TokenTypes.name)
        param = ast.Name(name_token.span, name_token.value)
        params.append(param)
        if not stream.consume_if(TokenTypes.comma):
            break
    return params


def _cond(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.if_):
        first = stream.consume(TokenTypes.if_)
        pred = _and(stream)
        stream.consume(TokenTypes.then)
        cons = _cond(stream)
        stream.consume(TokenTypes.else_)
        else_ = _cond(stream)
        return ast.Cond(merge(first.span, else_.span), pred, cons, else_)
    return _and(stream)


def _and(stream: TokenStream) -> ast.ASTNode:
    left = _or(stream)
    if stream.peek(TokenTypes.and_):
        op = stream.consume(TokenTypes.and_)
        right = _and(stream)
        return ast.FuncCall(
            merge(left.span, right.span),
            ast.FuncCall(merge(left.span, op.span), ast.Name(op.span, "and"), left),
            right,
        )
    return left


def _or(stream: TokenStream) -> ast.ASTNode:
    left = _not(stream)
    if stream.peek(TokenTypes.or_):
        op = stream.consume(TokenTypes.or_)
        right = _or(stream)
        return ast.FuncCall(
            merge(left.span, right.span),
            ast.FuncCall(merge(left.span, op.span), ast.Name(op.span, "or"), left),
            right,
        )
    return left


def _not(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.not_):
        op = stream.consume(TokenTypes.not_)
        operand = _not(stream)
        return ast.FuncCall(
            merge(op.span, operand.span),
            ast.Name(op.span, "not"),
            operand,
        )
    return _compare(stream)


def _compare(stream: TokenStream) -> ast.ASTNode:
    left = _add_sub_con(stream)
    if stream.peek(*COMPARE_OPS):
        op = stream.consume(*COMPARE_OPS)
        right = _compare(stream)
        return ast.FuncCall(
            merge(left.span, right.span),
            ast.FuncCall(
                merge(left.span, op.span),
                ast.Name(op.span, op.type_.value),
                left,
            ),
            right,
        )
    return left


def _add_sub_con(stream: TokenStream) -> ast.ASTNode:
    left = _mul_div_mod(stream)
    if stream.peek(TokenTypes.diamond, TokenTypes.plus, TokenTypes.dash):
        op = stream.consume(TokenTypes.diamond, TokenTypes.plus, TokenTypes.dash)
        right = _add_sub_con(stream)
        return ast.FuncCall(
            merge(left.span, right.span),
            ast.FuncCall(
                merge(left.span, op.span),
                ast.Name(op.span, op.type_.value),
                left,
            ),
            right,
        )
    return left


def _mul_div_mod(stream: TokenStream) -> ast.ASTNode:
    left = _exponent(stream)
    if stream.peek(TokenTypes.asterisk, TokenTypes.fslash, TokenTypes.percent):
        op = stream.consume(TokenTypes.asterisk, TokenTypes.fslash, TokenTypes.percent)
        right = _mul_div_mod(stream)
        return ast.FuncCall(
            merge(left.span, right.span),
            ast.FuncCall(
                merge(left.span, op.span),
                ast.Name(op.span, op.type_.value),
                left,
            ),
            right,
        )
    return left


def _exponent(stream: TokenStream) -> ast.ASTNode:
    result = _negate(stream)
    while stream.peek(TokenTypes.caret):
        op = stream.consume(TokenTypes.caret)
        other = _negate(stream)
        result = ast.FuncCall(
            merge(result.span, other.span),
            ast.FuncCall(merge(result.span, op.span), ast.Name(op.span, "^"), result),
            other,
        )
    return result


def _negate(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.dash):
        op = stream.consume(TokenTypes.dash)
        operand = _negate(stream)
        return ast.FuncCall(
            merge(op.span, operand.span), ast.Name(op.span, "~"), operand
        )
    return _func_call(stream)


def _func_call(stream: TokenStream) -> ast.ASTNode:
    result = _list(stream)
    while stream.consume_if(TokenTypes.lparen):
        while not stream.peek(TokenTypes.rparen):
            callee = _expr(stream)
            result = ast.FuncCall(merge(result.span, callee.span), result, callee)
            if not stream.consume_if(TokenTypes.comma):
                break
        stream.consume(TokenTypes.rparen)
    return result


def _list(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.lbracket):
        first = stream.consume(TokenTypes.lbracket)
        elements = _elements(stream, TokenTypes.rbracket)
        last = stream.consume(TokenTypes.rbracket)
        return ast.Vector(merge(first.span, last.span), ast.VectorTypes.LIST, elements)
    return _tuple(stream)


def _elements(stream: TokenStream, *end: TokenTypes) -> List[ast.ASTNode]:
    elements: List[ast.ASTNode] = []
    while not stream.peek(*end):
        elements.append(_expr(stream))
        if not stream.consume_if(TokenTypes.comma):
            break
    return elements


def _tuple(stream: TokenStream) -> ast.ASTNode:
    if stream.peek(TokenTypes.lparen):
        first = stream.consume(TokenTypes.lparen)
        elements = _elements(stream, TokenTypes.rparen)
        last = stream.consume(TokenTypes.rparen)
        if len(elements) == 1:
            return elements[0]
        return ast.Vector(merge(first.span, last.span), ast.VectorTypes.TUPLE, elements)
    return _scalar(stream)


def _scalar(stream: TokenStream) -> Union[ast.Name, ast.Scalar]:
    token = stream.consume(*SCALAR_TOKENS)
    if token.type_ == TokenTypes.name:
        return ast.Name(token.span, token.value)
    if token.type_ == TokenTypes.true:
        return ast.Scalar(token.span, ast.ScalarTypes.BOOL, "True")
    if token.type_ == TokenTypes.false:
        return ast.Scalar(token.span, ast.ScalarTypes.BOOL, "False")

    type_ = {
        TokenTypes.false: ast.ScalarTypes.BOOL,
        TokenTypes.float_: ast.ScalarTypes.FLOAT,
        TokenTypes.integer: ast.ScalarTypes.INTEGER,
        TokenTypes.string: ast.ScalarTypes.STRING,
        TokenTypes.true: ast.ScalarTypes.BOOL,
    }.get(token.type_)
    if type_ is None or token.value is None:
        raise UnexpectedTokenError(
            token,
            TokenTypes.false,
            TokenTypes.float_,
            TokenTypes.integer,
            TokenTypes.string,
            TokenTypes.true,
        )
    return ast.Scalar(token.span, type_, token.value)


_expr = _definition

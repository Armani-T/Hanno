from typing import cast, Union

from asts import base, typed, types
from errors import merge
from lex import TokenStream, TokenTypes

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
    return _program(stream)


def _program(stream: TokenStream) -> base.ASTNode:
    return _block(stream, TokenTypes.eof)
    # NOTE: We don't need to consume the EOF token because the stream
    # will be discarded after this anyway.


def _definition(stream: TokenStream) -> base.ASTNode:
    if not stream.peek(TokenTypes.let):
        return _pipe(stream)

    first = stream.consume(TokenTypes.let)
    target_token = stream.consume(TokenTypes.name)
    if stream.peek(TokenTypes.lparen):
        stream.consume(TokenTypes.lparen)
        params = _params(stream)
        stream.consume(TokenTypes.rparen)
        body = _body_clause(stream)
        return base.Define(
            merge(first.span, body.span),
            base.Name(target_token.span, target_token.value),
            base.Function.curry(merge(target_token.span, body.span), params, body),
        )

    target: base.Name
    if stream.consume_if(TokenTypes.colon):
        type_ann = _type(stream)
        target = typed.Name(target_token.span, type_ann, target_token.value)
    else:
        target = base.Name(target_token.span, target_token.value)

    body = _body_clause(stream)
    return base.Define(merge(first.span, body.span), target, body)


def _pipe(stream: TokenStream) -> base.ASTNode:
    left = _func(stream)
    if stream.peek(TokenTypes.pipe_greater):
        stream.consume(TokenTypes.pipe_greater)
        right = _pipe(stream)
        return base.FuncCall(merge(left.span, right.span), right, left)
    return left


def _func(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.bslash):
        first = stream.consume(TokenTypes.bslash)
        params = _params(stream)
        stream.consume(TokenTypes.arrow)
        body = _func(stream)
        return base.Function.curry(merge(first.span, body.span), params, body)
    return _cond(stream)


def _cond(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.if_):
        first = stream.consume(TokenTypes.if_)
        pred = _and(stream)
        stream.consume(TokenTypes.then)
        cons = _cond(stream)
        stream.consume(TokenTypes.else_)
        else_ = _cond(stream)
        return base.Cond(merge(first.span, else_.span), pred, cons, else_)
    return _and(stream)


def _and(stream: TokenStream) -> base.ASTNode:
    left = _or(stream)
    if stream.peek(TokenTypes.and_):
        op = stream.consume(TokenTypes.and_)
        right = _and(stream)
        return base.FuncCall(
            merge(left.span, right.span),
            base.FuncCall(merge(left.span, op.span), base.Name(op.span, "and"), left),
            right,
        )
    return left


def _or(stream: TokenStream) -> base.ASTNode:
    left = _not(stream)
    if stream.peek(TokenTypes.or_):
        op = stream.consume(TokenTypes.or_)
        right = _or(stream)
        return base.FuncCall(
            merge(left.span, right.span),
            base.FuncCall(merge(left.span, op.span), base.Name(op.span, "or"), left),
            right,
        )
    return left


def _not(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.not_):
        op = stream.consume(TokenTypes.not_)
        operand = _not(stream)
        return base.FuncCall(
            merge(op.span, operand.span),
            base.Name(op.span, "not"),
            operand,
        )
    return _compare(stream)


def _compare(stream: TokenStream) -> base.ASTNode:
    left = _add_sub_join(stream)
    if stream.peek(*COMPARE_OPS):
        op = stream.consume(*COMPARE_OPS)
        right = _compare(stream)
        return base.FuncCall(
            merge(left.span, right.span),
            base.FuncCall(
                merge(left.span, op.span),
                base.Name(op.span, op.type_.value),
                left,
            ),
            right,
        )
    return left


def _add_sub_join(stream: TokenStream) -> base.ASTNode:
    left = _mul_div_mod(stream)
    if stream.peek(TokenTypes.diamond, TokenTypes.plus, TokenTypes.dash):
        op = stream.consume(TokenTypes.diamond, TokenTypes.plus, TokenTypes.dash)
        right = _add_sub_join(stream)
        return base.FuncCall(
            merge(left.span, right.span),
            base.FuncCall(
                merge(left.span, op.span),
                base.Name(op.span, op.type_.value),
                left,
            ),
            right,
        )
    return left


def _mul_div_mod(stream: TokenStream) -> base.ASTNode:
    left = _exponent(stream)
    if stream.peek(TokenTypes.asterisk, TokenTypes.fslash, TokenTypes.percent):
        op = stream.consume(TokenTypes.asterisk, TokenTypes.fslash, TokenTypes.percent)
        right = _mul_div_mod(stream)
        return base.FuncCall(
            merge(left.span, right.span),
            base.FuncCall(
                merge(left.span, op.span),
                base.Name(op.span, op.type_.value),
                left,
            ),
            right,
        )
    return left


def _exponent(stream: TokenStream) -> base.ASTNode:
    result = _negate(stream)
    while stream.peek(TokenTypes.caret):
        op = stream.consume(TokenTypes.caret)
        other = _negate(stream)
        result = base.FuncCall(
            merge(result.span, other.span),
            base.FuncCall(merge(result.span, op.span), base.Name(op.span, "^"), result),
            other,
        )
    return result


def _negate(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.dash):
        op = stream.consume(TokenTypes.dash)
        operand = _negate(stream)
        return base.FuncCall(
            merge(op.span, operand.span), base.Name(op.span, "~"), operand
        )
    return _apply(stream)


def _apply(stream: TokenStream) -> base.ASTNode:
    result = _list(stream)
    while stream.consume_if(TokenTypes.lparen):
        while not stream.peek(TokenTypes.rparen):
            callee = _expr(stream)
            result = base.FuncCall(merge(result.span, callee.span), result, callee)
            if not stream.consume_if(TokenTypes.comma):
                break
        stream.consume(TokenTypes.rparen)
    return result


def _list(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.lbracket):
        first = stream.consume(TokenTypes.lbracket)
        elements = _elements(stream, TokenTypes.rbracket)
        last = stream.consume(TokenTypes.rbracket)
        return base.Vector(
            merge(first.span, last.span), base.VectorTypes.LIST, elements
        )
    return _tuple(stream)


def _elements(stream: TokenStream, *end: TokenTypes) -> list[base.ASTNode]:
    elements: list[base.ASTNode] = []
    while not stream.peek(*end):
        elements.append(_expr(stream))
        if not stream.consume_if(TokenTypes.comma):
            break
    return elements


def _tuple(stream: TokenStream) -> base.ASTNode:
    if stream.peek(TokenTypes.lparen):
        first = stream.consume(TokenTypes.lparen)
        elements = _elements(stream, TokenTypes.rparen)
        last = stream.consume(TokenTypes.rparen)
        if len(elements) == 1:
            return elements[0]
        return base.Vector(
            merge(first.span, last.span), base.VectorTypes.TUPLE, elements
        )
    return _scalar(stream)


def _scalar(stream: TokenStream) -> Union[base.Name, base.Scalar]:
    token = stream.consume(*SCALAR_TOKENS)
    type_: TokenTypes = token.type_
    value = cast(str, token.value)
    if type_ == TokenTypes.true:
        return base.Scalar(token.span, True)
    if type_ == TokenTypes.false:
        return base.Scalar(token.span, False)
    if type_ == TokenTypes.float_:
        return base.Scalar(token.span, float(value))
    if type_ == TokenTypes.string:
        return base.Scalar(token.span, value[1:-1])
    if type_ == TokenTypes.integer:
        return base.Scalar(token.span, int(value))
    return base.Name(token.span, value)


def _block(stream: TokenStream, *expected_ends: TokenTypes) -> base.ASTNode:
    if not expected_ends:
        raise ValueError("This function requires at least 1 expected `TokenTypes`.")

    exprs = []
    while not stream.peek(*expected_ends):
        expr = _expr(stream)
        stream.consume(TokenTypes.eol)
        exprs.append(expr)

    if not exprs:
        next_token = stream._advance()  # pylint: disable=W0212
        stream._push(next_token)  # pylint: disable=W0212
        return base.Vector.unit(next_token.span)
    if len(exprs) == 1:
        return exprs[0]
    return base.Block(merge(exprs[0].span, exprs[-1].span), exprs)


def _body_clause(stream: TokenStream) -> base.ASTNode:
    if stream.consume_if(TokenTypes.equal):
        return _expr(stream)

    stream.consume(TokenTypes.colon_equal)
    body = _block(stream, TokenTypes.end)
    stream.consume(TokenTypes.end)
    return body


def _params(stream: TokenStream) -> list[base.Name]:
    params: list[base.Name] = []
    while stream.peek(TokenTypes.name):
        name_token = stream.consume(TokenTypes.name)
        if stream.peek(TokenTypes.colon):
            stream.consume(TokenTypes.colon)
            param_type = _type(stream)
            param = typed.Name(name_token.span, param_type, name_token.value)
        else:
            param = base.Name(name_token.span, name_token.value)
        params.append(param)
        if not stream.consume_if(TokenTypes.comma):
            break

    if params:
        return params
    stream.consume(TokenTypes.name)


def _arrow_type(stream: TokenStream) -> types.Type:
    left = _tuple_type(stream)
    if stream.consume_if(TokenTypes.arrow):
        right = _arrow_type(stream)
        return types.TypeApply.func(merge(left.span, right.span), left, right)
    return left


def _tuple_type(stream: TokenStream) -> types.Type:
    if stream.peek(TokenTypes.lparen):
        first = stream.consume(TokenTypes.lparen)
        elements = []
        while not stream.peek(TokenTypes.rparen):
            element = _type(stream)
            elements.append(element)
            if not stream.consume_if(TokenTypes.comma):
                break

        last = stream.consume(TokenTypes.rparen)
        span = merge(first.span, last.span)
        if not elements:
            return types.TypeName.unit(span)
        if len(elements) == 1:
            return elements[0]
        return types.TypeApply.tuple_(span, elements)

    return _generic(stream)


def _generic(stream: TokenStream) -> types.Type:
    base_token = stream.consume(TokenTypes.name)
    type_ = types.TypeName(base_token.span, base_token.value)
    # TODO: Add a  later phase where the type names (generated above)
    # that are not in scope are turned into type vars instead.

    if stream.consume_if(TokenTypes.lbracket):
        while not stream.peek(TokenTypes.rparen):
            arg = _type(stream)
            type_ = types.TypeApply(merge(type_.span, arg.span), left, right)
            if not stream.consume_if(TokenTypes.comma):
                break
    return type_


_expr = _definition
_type = _arrow_type

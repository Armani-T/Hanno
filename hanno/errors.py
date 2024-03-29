from enum import auto, Enum
from json import dumps
from textwrap import wrap
from typing import Optional, Tuple, TypedDict

from asts.base import Pattern, UnitPattern
from asts.types_ import Type, TypeApply, TypeName
from log import logger
from format import show_pattern, show_type

JSONResult = TypedDict("JSONResult", {"source_path": str, "error_name": str})
Span = Tuple[int, int]

LINE_WIDTH = 87
# NOTE: For some reason, this value has to be off by one. So the line
#  width is actually `88` in this case.

wrap_text = lambda string: "\n".join(
    wrap(
        string,
        width=LINE_WIDTH,
        tabsize=4,
        drop_whitespace=False,
        replace_whitespace=False,
    )
)


class CMDErrorReasons(Enum):
    """The reasons that the exception could have been thrown."""

    NOT_FOUND = auto()
    IS_FOLDER = auto()
    NO_PERMISSION = auto()


class ResultTypes(Enum):
    """The different ways that an error message can be formed."""

    ALERT_MESSAGE = auto()
    JSON = auto()
    LONG_MESSAGE = auto()


class PatternPosition(Enum):
    """The places that an irrefutable pattern could have been found."""

    CASE = auto()
    PARAMETER = auto()
    TARGET = auto()


def merge(left_span: Span, right_span: Span) -> Span:
    """
    Combine two token spans to get the maximum possible range.

    Parameters
    ----------
    left_span: Span
        The first span.
    right_span: Span
        The second span.

    Returns
    -------
    The maximum possible span.
    """
    start = min(left_span[0], right_span[0])
    end = max(left_span[1], right_span[1])
    return start, end


def to_json(error: Exception, source: str, filename: str) -> str:
    """
    Report an error in JSON format.

    Parameters
    ----------
    error: CompilerError
        The error to be reported on.
    source: str
        The source code of the program which will probably be quoted in
        the error message.
    filename: str
        The name of the file from which the error came.

    Returns
    -------
    str
        A JSON string containing all the error data.
    """
    return (
        dumps(error.to_json(source, filename))
        if isinstance(error, CompilerError)
        else handle_other_exceptions(error, ResultTypes.JSON, filename)
    )


def to_alert_message(error: Exception, source: str, filename: str) -> str:
    """
    Report an error by formatting it for the terminal. This function
    prints out the shorter version of the same error message as
    `report_terminal_long`.

    Parameters
    ----------
    error: CompilerError
        The error to be reported on.
    source: str
        The source code of the program which will probably be quoted in
        the error message.
    filename: str
        The name of the file from which the error came.

    Returns
    -------
    str
        A beautified string containing all the error data.
    """
    if isinstance(error, CompilerError):
        message, span = error.to_alert_message(source, filename)
        return message if span is None else f"{span[0]} | {message}"
    return handle_other_exceptions(error, ResultTypes.ALERT_MESSAGE, filename)


def to_long_message(error: Exception, source: str, filename: str) -> str:
    """
    Generate a longer explanation of the error for the user.

    This method prints out the more informative error message. If
    possible, the error message should have some suggestions on how
    to fix the problem. This method should be used for things like
    generating an error report at the terminal.

    Parameters
    ----------
    error: CompilerError
        The error to be reported on.
    source: str
        The source code of the program which will probably be quoted in
        the error message.
    filename: str
        The name of the file from which the error came.

    Returns
    -------
    str
        A beautified string containing all the error data.
    """
    if isinstance(error, CompilerError):
        plain_message = error.to_long_message(source, filename)
        return beautify(plain_message, filename)
    return handle_other_exceptions(error, ResultTypes.LONG_MESSAGE, filename)


def handle_other_exceptions(
    error: Exception, result_type: ResultTypes, filename: str
) -> str:
    """
    Generate a user-friendly message for exceptions outside the
    `CompilerError` hierarchy. The message should adhere to the
    same rules as the function corresponding to the `result_type`
    passed in.

    Parameters
    ----------
    error: Exception
        The exception that the message is based on.
    result_type: ResultTypes
        What rules the message should conform to.
    filename: str
        The file that was being run when the exceptions were raised.

    Returns
    -------
    str
        A user-friendly message based on the exception passed in.
    """
    logger.error(
        "Unknown error condition: %s( %s )",
        error.__class__.__name__,
        ", ".join(map(str, error.args)),
        exc_info=True,
    )
    if result_type == ResultTypes.JSON:
        return dumps(
            {
                "source_path": filename,
                "error_name": "internal_error",
                "actual_error": error.__class__.__name__,
            }
        )
    if result_type == ResultTypes.ALERT_MESSAGE:
        return wrap_text(
            f"Internal Error: Encountered unknown error condition: "
            f'"{type(error).__name__}".'
        )
    return beautify(
        wrap_text(
            f"Internal Error: Encountered unknown error condition: "
            f'"{error.__class__.__name__}". Please check the log file for more '
            "details."
        ),
        filename,
    )


def relative_pos(abs_pos: int, source: str) -> Span:
    """
    Get the column and line number of a character in some source code
    given the position of a character.

    Parameters
    ----------
    abs_pos: int
        The position of a character inside `source`.
    source: str
        The source code that the character's position came from.

    Returns
    -------
    Span
        The relative position with the column and the line number.
    """
    max_len = len(source)
    if abs_pos >= max_len:
        logger.fatal(
            "The absolute position (%d) is >= len(source) (%d)", abs_pos, max_len
        )
        raise ValueError(
            f"The absolute position ({abs_pos}) cannot be equal to or bigger than "
            f"the size of the entire source file ({len(source)})."
        )

    column = max(((abs_pos - source.rfind("\n", 0, abs_pos)) - 1), 0)
    line = 1 + source.count("\n", 0, abs_pos)
    return column, line


def make_pointer(span: Span, source: str) -> str:
    """
    Make an arrow that points to a specific section of a line in
    `source`.

    Notes
    -----
    - This class assumes that `span` starts and ends on the same line
      of source code. This will be updated later.

    Parameters
    ----------
    span: Span
        The section of code that is supposed to be pointed to.
    source: str
        The source code used to find the arrow position. The line that
        the arrow is pointing to is paired with the arrow, so we need
        to get it from the source code.

    Returns
    -------
    str
        The line of source code with a problem with the arrow that
        points specifically to the offending token.
    """
    span_start, span_end = span
    start_column, line_number = relative_pos(span_start, source)
    line_start = 1 + source.rfind("\n", 0, span_start)
    line_end = source.find("\n", span_start)
    source_line = source[line_start:] if line_end == -1 else source[line_start:line_end]
    preface = f"{line_number} "
    return (
        f"{preface}|{source_line}\n{' ' * len(preface)}|"
        f"{'_' * (span_start - line_start)}{'^' * (span_end - span_start)}"
    )


def beautify(message: str, path: str) -> str:
    """
    Make an error message look good before printing it to the terminal.

    Notes
    -----
    - If LINE_WIDTH < 17, the function will assume 17 is the line width

    Parameters
    ----------
    message: str
        The plain error message before formatting.
    path: str
        The file from which the error came.

    Returns
    -------
    str
        The error message after formatting.
    """
    head = (
        "Error Encountered"
        if LINE_WIDTH < 24
        else " Error Encountered ".center(LINE_WIDTH, "=")
    )
    return f'\n{head}\nFrom "{path}":\n\n{message}\n\n{"=" * max(17, LINE_WIDTH)}\n'


def _is_func_type(type_: Type) -> bool:
    return (
        isinstance(type_, TypeApply)
        and isinstance(type_.caller, TypeApply)
        and isinstance(type_.caller.caller, TypeName)
        and type_.caller.caller == TypeName((0, 0), "->")
    )


class CompilerError(Exception):
    """
    This base exception for the entire program. It should never be
    caught or thrown directly, one of its subclasses should be used
    instead.

    Methods
    -------
    to_alert_message(source, source_path)
        Generate a short description of the error for the user.
    to_long_message(source, source_path)
        Generate a longer explanation of the error for the user.
    to_json(source, source_path)
        Generate an error report in JSON format.
    """

    def to_alert_message(
        self, source: str, source_path: str
    ) -> Tuple[str, Optional[Span]]:
        """
        Generate a short description of the error for the user.

        This method prints out a shorter, more direct error message. It
        should be used for editor tooltips and alerts rather than
        generating a standalone error message for the user.

        Parameters
        ----------
        source: str
            The source code of the file that the error came from.
        source_path: str
            The path to the file that the error came from.

        Returns
        -------
        Tuple[str, Optional[Span]]
            The generated message and either the relative position of
            the expression that caused the error or `None` if it is not
            needed.
        """

    def to_long_message(self, source: str, source_path: str) -> str:
        """
        Generate a longer explanation of the error for the user.

        This method prints out the more informative error message. If
        possible, the error message should have some suggestions on how
        to fix the problem. This method should be used for things like
        generating an error report at the terminal.

        Parameters
        ----------
        source: str
            The source code of the file that the error came from.
        source_path: str
            The path to the file that the error came from.

        Returns
        -------
        str
            The final error message but without any external formatting.
        """

    def to_json(self, source: str, source_path: str) -> JSONResult:
        """
        Generate an error report in JSON format.

        This method should be used for things like sending info to a
        server to generate a more full error report. In general, the
        JSON message should contain enough data to run the
        `to_long_message` method.

        Parameters
        ----------
        source: str
            The source code of the file that the error came from.
        source_path: str
            The path to the file that the error came from.

        Returns
        -------
        JSONResult
            The full error report as a single `dict` object that can
            be converted into a JSON object.
        """


class BadEncodingError(CompilerError):
    """
    This is an error where a source text from a file cannot be decoded
    by the lexer.
    """

    name = "unknown_encoding"

    def __init__(self, encoding: str) -> None:
        super().__init__()
        self.encoding: str = encoding

    def to_json(self, _, source_path):
        return {
            "error_name": self.name,
            "source_path": source_path,
            "encoding": self.encoding,
        }

    def to_alert_message(self, _, source_path):
        return f'The file "{source_path}" has an unknown encoding.', None

    def to_long_message(self, _, source_path):
        middle_sentence = (
            f"We have tried using the {self.encoding} encoding but it has failed. "
            if self.encoding is not None
            else ""
        )
        return wrap_text(
            f'The file "{source_path}" has an unknown encoding. {middle_sentence}Try '
            "changing the file's encoding to UTF-8 and running it again."
        )


class CircularTypeError(CompilerError):
    """
    This is an error where 2 types are supposed to be unified but one
    type (`inner`) occurs inside the other (`outer`), leading to an
    infinitely recursive substitution.
    """

    name = "circular_type_error"

    def __init__(self, inner: Type, outer: Type) -> None:
        super().__init__()
        self.inner: Type = inner
        self.outer: Type = outer

    def to_json(self, _, source_path):
        return {
            "error_name": self.name,
            "inner": show_type(self.inner),
            "outer": show_type(self.outer),
            "source_path": source_path,
        }

    def to_alert_message(self, _, __):
        inner = show_type(self.inner)
        outer = show_type(self.outer, True)
        return (
            f"`{inner}` was found inside `{outer}` so the types here cannot "
            "be inferred."
        )

    def to_long_message(self, source, _):
        explanation = (
            f"The type `{show_type(self.inner)}` (the type of the first expression "
            f"above) was found inside the type of `{show_type(self.outer)}` (the type "
            "of the second expression above), meaning that they are infinitely "
            "recursive. Because of this, it is impossible to infer the types of both "
            "expressions."
        )
        return "\n\n".join(
            (
                make_pointer(self.inner.span, source),
                make_pointer(self.outer.span, source),
                wrap_text(explanation),
            )
        )


class CMDError(CompilerError):
    """
    This is an error where some part of setting up the program using
    arguments from the command line fails.
    """

    name = "command_line_error"

    def __init__(self, reason: CMDErrorReasons):
        super().__init__()
        self.reason: CMDErrorReasons = reason

    def to_json(self, _, source_path):
        return {
            "error_name": self.name,
            "specific_error": self.reason.name.lower(),
            "source_path": source_path,
        }

    def to_alert_message(self, source, source_path):
        message = {
            CMDErrorReasons.NOT_FOUND: f'The file "{source_path}" couldn\'t be found.',
            CMDErrorReasons.IS_FOLDER: f'The path "{source_path}" points to a folder.',
            CMDErrorReasons.NO_PERMISSION: (
                f'Unable to read the file "{source_path}" since we don\'t have the '
                "required permissions."
            ),
        }[self.reason]
        return message, None

    def to_long_message(self, source, source_path):
        default_message = "Unable to open and read the file due to an internal error."
        message = {
            CMDErrorReasons.NOT_FOUND: (
                f'The file "{source_path}" could not be found, please check if the '
                "path given is correct and if the file still exists."
            ),
            CMDErrorReasons.NO_PERMISSION: (
                f'We were unable to open the file "{source_path}" because we '
                "don't have the necessary permissions. Please grant the compiler "
                "file read permissions then try again."
            ),
            CMDErrorReasons.IS_FOLDER: (
                f'We were unable to open the file at "{source_path}" because it is '
                "a folder rather than a file. Try rerunning the command using a file "
                "within the folder instead."
            ),
        }.get(self.reason, default_message)
        return wrap_text(message)


class FatalInternalError(CompilerError):
    """
    This is an error where the program reaches an illegal state, and
    the best way to fix it is to restart.
    """

    name = "internal_error"

    def to_json(self, _, source_path):
        return {"error_name": self.name, "source_path": source_path}

    def to_alert_message(self, _, __):
        return "A fatal error occurred in the compiler.", None

    def to_long_message(self, _, __):
        return wrap_text(
            "The compiler has stopped running due to a fatal error. For more info, "
            "check the log file."
        )


class IllegalCharError(CompilerError):
    """
    This is an error where the lexer finds a character that it
    either cannot recognise or doesn't expect.
    """

    name = "illegal_char"

    def __init__(self, span: Span, char: str) -> None:
        super().__init__()
        self.span: Span = span
        self.char: str = char

    def to_json(self, source, source_path):
        return {
            "source_path": source_path,
            "error_name": self.name,
            "char": self.char,
            "start": self.span[0],
            "end": self.span[1],
        }

    def to_alert_message(self, source, source_path):
        message = (
            "This string doesn't have an end marker."
            if self.char == '"'
            else "This character is not allowed here."
        )
        return message, relative_pos(self.span[0], source)

    def to_long_message(self, source, source_path):
        if self.char == '"':
            explanation = (
                "This string doesn't have a final '\"' so we can't read the rest of "
                "the file. You can fix this by adding a '\"' where the string is "
                "supposed to end."
            )
        else:
            explanation = (
                f'This character ( "{self.char}" ) cannot be parsed. Please try '
                "removing it."
            )
        return f"{make_pointer(self.span, source)}\n\n{wrap_text(explanation)}"


class NumberOverflowError(CompilerError):
    """
    An error where the code generator cannot finish generating the
    bytecode there was a number that was too big for the space
    allocated.
    """

    name = "overflow_error"

    def to_json(self, _, source_path):
        return {"error_name": self.name, "source_path": source_path}

    def to_alert_message(self, source, source_path):
        return "Cannot complete code generation due to overflow.", None

    def to_long_message(self, source, source_path):
        message = (
            "A number was used in the code that was too big to be encoded in the "
            "bytecode for execution."
        )
        return wrap_text(message)


class RefutablePatternError(CompilerError):
    """
    This is an error where an exhaustive pattern is
    expected but a non-exhaustive (i.e. refutable) one is found instead.
    """

    name = "refutable_pattern"

    def __init__(self, position: PatternPosition, pattern: Optional[Pattern]) -> None:
        super().__init__()
        self.pattern: Pattern = pattern
        self.position: PatternPosition = position
        self.span: Span = pattern.span

    @classmethod
    def empty_match(cls, span: Span):
        instance = cls(PatternPosition.CASE, UnitPattern(span))
        instance.pattern = None
        return instance

    def to_json(self, source, source_path):
        json = {
            "source_path": source_path,
            "error_name": "empty_match" if self.pattern is None else self.name,
            "position": self.position.name.lower(),
            "start": self.span[0],
            "end": self.span[1],
        }
        if self.pattern is not None:
            json["pattern"] = show_pattern(self.pattern)
        return json

    def to_alert_message(self, source, source_path):
        if self.pattern is None:
            return (
                "Match cases must have an exhaustive case.",
                self.span,
            )

        header = f'"{show_pattern(self.pattern)}" is not exhaustive. '
        explanation = (
            "Only exhaustive patterns are allowed to be definition targets."
            if self.position is PatternPosition.TARGET
            else (
                "Only exhaustive patterns are allowed in function parameters."
                if self.position is PatternPosition.PARAMETER
                else "Match cases are required to have an exhaustive case."
            )
        )
        return header + explanation, self.span

    def to_long_message(self, source, source_path):
        if self.pattern is None:
            explanation = (
                "Match expressions must have at least one branch since the program "
                "will always fail if it has none (because the match pattern will "
                "always fail)."
            )
        elif self.position is PatternPosition.CASE:
            explanation = (
                "Match expressions need an exhaustive case to ensure that they can "
                "always produce a result. A partial match case could make the program "
                f'fail. You can fix this by changing "{show_pattern(self.pattern)}" '
                "to a pattern that can't fail."
            )
        else:
            position = (
                "definition targets"
                if self.position is PatternPosition.TARGET
                else (
                    "function parameters"
                    if self.position is PatternPosition.TARGET
                    else "match cases"
                )
            )
            explanation = (
                f"Only patterns that can't fail are allowed in {position} since a "
                "partial definition here could make the program fail. You can fix "
                f'this by changing "{show_pattern(self.pattern)}" to a pattern that '
                "can't fail."
            )
        return f"{make_pointer(self.span, source)}\n\n{wrap_text(explanation)}"


class TypeMismatchError(CompilerError):
    """
    This is caused by the two types in an equation not being equal
    when they're supposed to be.
    """

    name = "type_mismatch"

    def __init__(self, left: Type, right: Type) -> None:
        super().__init__()
        self.left: Type = left
        self.right: Type = right

    def to_json(self, source, source_path):
        return {
            "source_path": source_path,
            "error_name": self.name,
            "actual_type": {
                "start": self.left.span[0],
                "end": self.left.span[1],
                "type": show_type(self.left),
            },
            "expected_type": {
                "start": self.right.span[0],
                "end": self.right.span[1],
                "type": show_type(self.right),
            },
        }

    def to_alert_message(self, source, source_path):
        explanation = (
            f"The type `{show_type(self.left)}` was inferred here, but "
            f"`{show_type(self.right)}` was expected here instead."
        )
        return explanation, self.left.span

    def use_func_message(self) -> bool:
        return (_is_func_type(self.left) and not _is_func_type(self.right)) or (
            _is_func_type(self.right) and not _is_func_type(self.left)
        )

    def to_long_message(self, source, source_path):
        if self.use_func_message():
            first, last = self.right, self.left
            inner_message = (
                "The expression above required a function of type "
                f"`{show_type(first)}`. But it got a `{show_type(last)}` instead, "
                "from the expression:"
            )
        else:
            first, last = self.left, self.right
            inner_message = (
                f"This value has an unexpected type `{show_type(self.left)}`. "
                f"The value was expected to have the type `{show_type(self.right)}` "
                "instead, like in this expression:"
            )
        return "\n\n".join(
            (
                make_pointer(first.span, source),
                wrap_text(inner_message),
                make_pointer(last.span, source),
            )
        )


class UndefinedNameError(CompilerError):
    """
    This is an error where the program tries to refer to a name that
    has not been defined yet.
    """

    name = "undefined_name"

    def __init__(self, name):
        super().__init__()
        self.span: Span = name.span
        self.value: str = name.value

    def to_json(self, source, source_path):
        return {
            "source_path": source_path,
            "error_name": self.name,
            "start": self.span[0],
            "end": self.span[1],
            "value": self.value,
        }

    def to_alert_message(self, source, source_path):
        return f'The name "{self.value}" has not been defined yet.', self.span

    def to_long_message(self, source, source_path):
        explanation = wrap_text(
            f'The name "{self.value}" is being used but it hasn\'t been defined.'
        )
        return f"{make_pointer(self.span, source)}\n\n{explanation}"


class UnexpectedEOFError(CompilerError):
    """
    This is an error where the stream of lexer tokens ends in the
    middle of a parser rule.
    """

    name = "unexpected_eof"

    def __init__(self, expected: Optional[str] = None) -> None:
        super().__init__()
        self.expected: Optional[str] = expected

    def to_json(self, source, source_path):
        pos = len(source) - 1
        return {
            "source_path": source_path,
            "error_name": self.name,
            "start": pos - 1,
            "end": pos,
            "expected": self.expected,
        }

    def to_alert_message(self, source, source_path):
        rel_pos = relative_pos(len(source) - 1, source)
        if self.expected is None:
            return "End of file unexpectedly reached.", rel_pos
        return f"End of file reached before parsing {self.expected}.", rel_pos

    def to_long_message(self, source, source_path):
        return wrap_text("The file unexpectedly ended before parsing was finished.")


class UnexpectedTokenError(CompilerError):
    """
    This is an error where the parser `peek`s and finds a token that
    is different from what it expected.
    """

    name = "unexpected_token"

    def __init__(self, token, *expected) -> None:
        super().__init__()
        self.span = token.span
        self.found_type = token.type_
        self.expected = expected

    def to_json(self, source, source_path):
        return {
            "source_path": source_path,
            "error_name": self.name,
            "start": self.span[0],
            "end": self.span[1],
            "expected": (token.value for token in self.expected),
        }

    def to_alert_message(self, source, source_path):
        quoted_parts = [f'"{exp.value}"' for exp in self.expected]
        if not self.expected:
            message = "Unexpected token found."
        elif len(quoted_parts) == 1:
            message = f"Expected to find {quoted_parts[0]} here instead."
        else:
            *body, tail = quoted_parts
            message = f"Expected to find {', '.join(body)} or {tail} here instead."
        return message, self.span[0]

    def to_long_message(self, source, source_path):
        if not self.expected:
            explanation = wrap_text("Unexpected expression found here.")
            return f"{make_pointer(self.span, source)}\n\n{explanation}"
        if len(self.expected) < 4:
            explanation = wrap_text(
                "We expected to find "
                + " or ".join(f'"{exp.value}"' for exp in self.expected)
                + " here instead."
            )
            return f"{make_pointer(self.span, source)}\n\n{explanation}"

        *body, tail = [f'"{exp.value}"' for exp in self.expected]
        body_text = ", ".join(body)
        explanation = wrap_text(f"We expected to find {body_text} or {tail} here.")
        return f"{make_pointer(self.span, source)}\n\n{explanation}"

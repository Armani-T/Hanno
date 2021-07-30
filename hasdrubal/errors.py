from enum import auto, Enum
from json import dumps
from textwrap import wrap
from typing import Optional, Tuple, TypedDict

from log import logger
from pprint_ import ASTPrinter

LINE_WIDTH = 87
LITERALS = ("float_", "integer", "name", "string")

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
    FILE_NOT_FOUND = auto()
    NO_PERMISSION = auto()


class JSONResult(TypedDict, total=False):
    source_path: str
    error_name: str


def merge(left_span: Tuple[int, int], right_span: Tuple[int, int]) -> Tuple[int, int]:
    """
    Combine two token spans to get the maximum possible range.

    Parameters
    ----------
    left_span: Tuple[int, int]
        The first span.
    right_span: Tuple[int, int]
        The second span.

    Returns
    -------
    The maximum possible span.
    """
    start = min(left_span[0], right_span[0])
    end = max(left_span[1], right_span[1])
    return start, end


def to_json(error: "HasdrubalError", source: str, filename: str) -> str:
    """
    Report an error in JSON format.

    Parameters
    ----------
    error: HasdrubalError
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
    try:
        result = error.to_json(source, filename)
    except AttributeError:
        logger.error(
            "Unknown error condition: %s( %s )",
            type(error).__name__,
            ", ".join(map(str, error.args)),
            exc_info=True,
        )
        result = {
            "source_path": filename,
            "error_name": "internal_error",
            "actual_error_name": type(error).__name__,  # type: ignore
        }
    return dumps(result)


def to_alert_message(error: "HasdrubalError", source: str, filename: str) -> str:
    """
    Report an error by formatting it for the terminal. This function
    prints out the shorter version of the same error message as
    `report_terminal_long`.

    Parameters
    ----------
    error: HasdrubalError
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
    try:
        message, span = error.to_alert_message(source, filename)
        return message if span is None else f"{span[1]} | {message}"
    except AttributeError:
        logger.error(
            "Unknown error condition: %s( %s )",
            error.__class__.__name__,
            ", ".join(map(str, error.args)),
            exc_info=True,
        )
        return wrap_text(
            f"Internal Error: Encountered unknown error condition: "
            f'"{error.__class__.__name__}".'
        )


def to_long_message(error: "HasdrubalError", source: str, filename: str) -> str:
    """
    Generate a longer explanation of the error for the user.

    This method prints out the more informative error message. If
    possible, the error message should have some suggestions on how
    to fix the problem. This method should be used for things like
    generating an error report at the terminal.

    Parameters
    ----------
    error: HasdrubalError
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
    try:
        return beautify(
            error.to_long_message(source, filename),
            filename,
            getattr(error, "pos", None),
            source,
        )
    except AttributeError:
        logger.error(
            "Unknown error condition: %s( %s )",
            error.__class__.__name__,
            ", ".join(map(str, error.args)),
            exc_info=True,
        )
        return beautify(
            wrap_text(
                f"Internal Error: Encountered unknown error condition: "
                f'"{type(error).__name__}". Check the log file for more details.'
            ),
            filename,
            None,
            "",
        )


def relative_pos(pos: int, source: str) -> Tuple[int, int]:
    """
    Get the column and line number of a character in some source code
    given the position of a character.

    Parameters
    ----------
    pos: int
        The position of a character inside of `source`.
    source: str
        The source code that the character's position came from.

    Returns
    -------
    Tuple[int, int]
        The relative position with the column and the line number.
    """
    cut_source = source[:pos]
    column = max(((pos - cut_source.rfind("\n")) - 1), 0)
    line = 1 + cut_source.count("\n")
    return (column, line)


def make_pointer(pos: int, source: str) -> str:
    """
    Make an arrow that points to a specific position in a line from
    `source`.

    Parameters
    ----------
    source: str
        The source code used to find the position of the arrow. The
        line that the arrow is pointing to is paired with the arrow
        so we need to get it from the source code.
    pos: int
        The absolute position of the arrow in the source code.

    Returns
    -------
    str
        The line of source code with a problem with the arrow that
        points specifically to the offending token.
    """
    column, line = relative_pos(pos, source)
    start = 1 + source.rfind("\n", 0, pos)
    end = source.find("\n", pos)
    source_line = source[start:] if end == -1 else source[start:end]
    preface = f"{line} |"
    return f"{preface}{source_line}\n{' ' * (len(preface) - 1)}|{'-'* column}^"


def beautify(
    message: str,
    file_path: str,
    pos: Optional[int],
    source: str,
) -> str:
    """
    Make an error message look good before printing it to the terminal.

    Parameters
    ----------
    message: str
        The plain error message before formatting.
    file_path: str
        The file from which the error came.
    pos: Optional[int]
        If it is not `None`, add an arrow that points to the
        token that caused the error.
    source: str
        The source code which will be quoted in the formatted error
        message. If `pos` is None, then this argument will not be used
        at all.

    Returns
    -------
    str
        The error message after formatting.
    """
    head = (
        "Error Encountered:"
        if LINE_WIDTH <= 20
        else " Error Encountered ".center(LINE_WIDTH, "=")
    )
    message = message if pos is None else f"{make_pointer(pos, source)}\n\n{message}"
    path = wrap_text(f'In file "{file_path}":')
    tail = "=" * LINE_WIDTH
    return f"\n{head}\n{path}\n\n{message}\n\n{tail}\n"


class HasdrubalError(Exception):
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
    ) -> Tuple[str, Optional[Tuple[int, int]]]:
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
        Tuple[str, Optional[int]]
            A tuple containing the generated message and either `None`
            or the positional data. If the positional data is needed,
            it will be added to the actual message.
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


class BadEncodingError(HasdrubalError):
    """
    This is an error where a source text from a file cannot be decoded
    by the lexer.
    """

    def to_json(self, _, source_path):
        return {
            "error_name": "unknown_encoding",
            "source_path": source_path,
        }

    def to_alert_message(self, _, source_path):
        return (f'The file "{source_path}" has an unknown encoding.', None)

    def to_long_message(self, _, source_path):
        return (
            f'The file "{source_path}" has an unknown encoding. Try converting the '
            "file's encoding to UTF-8 and running it again."
        )


class CMDError(HasdrubalError):
    """
    This is an error where some part of setting up the program using
    arguments from the command line fails.
    """

    def __init__(self, reason: CMDErrorReasons):
        super().__init__()
        self.reason: CMDErrorReasons = reason

    def to_json(self, _, source_path):
        return {"error_name": self.reason.name.lower(), "source_path": source_path}

    def to_alert_message(self, source, source_path):
        message = {
            CMDErrorReasons.FILE_NOT_FOUND: (
                f'The file "{source_path}" was not found.'
            ),
            CMDErrorReasons.NO_PERMISSION: (
                f'Unable to read the file "{source_path}" since we don\'t have the'
                " necessary permissions."
            ),
        }[self.reason]
        return (message, None)

    def to_long_message(self, source, source_path):
        default_message = "Unable to open and read the file due to an internal error."
        message = {
            CMDErrorReasons.FILE_NOT_FOUND: (
                f'The file "{source_path}" could not be found, please check if the'
                " path is correct and if the file still exists."
            ),
            CMDErrorReasons.NO_PERMISSION: (
                f'We were unable to open the file "{source_path}" because we'
                " do not have the necessary permissions. Please grant the program"
                " those permissions first."
            ),
        }.get(self.reason, default_message)
        return wrap_text(message)


class FatalInternalError(HasdrubalError):
    """
    This is an error where the program reaches an illegal state, and
    the best way to fix it is to restart.
    """

    def to_json(self, _, source_path):
        return {"error_name": "internal_error", "source_path": source_path}

    def to_alert_message(self, _, __):
        return ("A fatal error has occurred inside the runtime.", None)

    def to_long_message(self, _, __):
        return wrap_text(
            "Hasdrubal was unable to continue running due to a fatal error inside the "
            "runtime. For more information, check the log file."
        )


class IllegalCharError(HasdrubalError):
    """
    This is an error where the lexer finds a character that it
    either cannot recognise or doesn't expect.
    """

    def __init__(self, span: int, char: str) -> None:
        super().__init__()
        self.span: int = span
        self.char: str = char

    def to_json(self, source, source_path):
        column, line = relative_pos(len(source) - 1, source)
        return {
            "source_path": source_path,
            "error_name": "illegal_char",
            "line": line,
            "column": column,
            "char": self.char,
        }

    def to_alert_message(self, source, source_path):
        message = (
            "This string doesn't have an end marker."
            if self.char == '"'
            else "This character is not allowed here."
        )
        return (message, self.span)

    def to_long_message(self, source, source_path):
        if self.char == '"':
            explanation = (
                "The string that starts here has no final '\"' so it covers the rest "
                "of the file can't be parsed. You can fix this by adding a '\"' where "
                "the string is actually supposed to end."
            )
        else:
            explanation = (
                f'This character ( "{self.char}" ) cannot be parsed. Please try '
                "removing it."
            )
        return f"{make_pointer(self.span, source)}\n\n{wrap_text(explanation)}"


class TypeMismatchError(HasdrubalError):
    """
    This error is caused by the compiler's type inferer being unable to
    unify the two sides of a type equation.
    """

    def __init__(self, left, right) -> None:
        super().__init__()
        self.left = left
        self.right = right

    def to_json(self, source, source_path):
        printer = ASTPrinter()
        left_column, left_line = relative_pos(source, self.left.span[0])
        right_column, right_line = relative_pos(source, self.right.span[0])
        return {
            "source_path": source_path,
            "error_name": "type_mismatch",
            "type_1": {
                "column": left_column,
                "line": left_line,
                "type": printer.run(self.left),
            },
            "type_2": {
                "column": right_column,
                "line": right_line,
                "type": printer.run(self.right),
            },
        }

    def to_long_message(self, source, source_path):
        printer = ASTPrinter()
        return "\n\n".join(
            (
                f"{make_pointer(self.left.span[0], source)}",
                "This value has an unexpected type. It has the type:",
                f"    {printer.run(self.left)}",
                "but the type is supposed to be:",
                f"    {printer.run(self.right)}",
                "like it is here:",
                f"{make_pointer(self.right.span[0], source)}",
            )
        )

    def to_alert_message(self, source, source_path):
        printer = ASTPrinter()
        explanation = (
            f"Unexpected type `{printer.run(self.left)}` where "
            f"`{printer.run(self.right)}` was expected instead."
        )
        return (explanation, relative_pos(source, self.left.span[0]))


class UndefinedNameError(HasdrubalError):
    """
    This is an error where the program tries to refer to a name that
    has not been defined yet.
    """

    def __init__(self, name):
        super().__init__()
        self.span: Tuple[int, int] = name.span
        self.value: str = name.value

    def to_json(self, source, source_path):
        column, line = relative_pos(source, self.span[0])
        return {
            "source_path": source_path,
            "error_name": "undefined_name",
            "line": line,
            "column": column,
            "value": self.value,
        }

    def to_alert_message(self, source, source_path):
        return (
            f'Undefined name "{self.value}" found.',
            relative_pos(source, self.span[0]),
        )

    def to_long_message(self, source, source_path):
        explanation = wrap_text(
            f'The name "{self.value}" is being used but it has not been defined yet.'
        )
        return f"{make_pointer(self.span[0], source)}\n\n{explanation}"


class UnexpectedEOFError(HasdrubalError):
    """
    This is an error where the stream of lexer tokens ends in the
    middle of a parser rule.
    """

    def __init__(self, expected: Optional[str] = None) -> None:
        super().__init__()
        self.expected: Optional[str] = expected

    def to_json(self, source, source_path):
        column, line = relative_pos(len(source) - 1, source)
        return {
            "source_path": source_path,
            "error_name": "unexpected_end",
            "line": line,
            "column": column,
            "expected": self.expected,
        }

    def to_alert_message(self, source, source_path):
        pos = len(source) - 1
        if self.expected is None:
            return (f"End of file reached before parsing {self.expected}.", pos)
        return ("End of file unexpectedly reached.", pos)

    def to_long_message(self, source, source_path):
        explanation = wrap_text("The file ended before I could finish parsing it.")
        return f"{make_pointer(len(source) - 1, source)}\n\n{explanation}"


class UnexpectedTokenError(HasdrubalError):
    """
    This is an error where the parser `peek`s and finds a token that
    is different from what it expected.
    """

    def __init__(self, token, *expected) -> None:
        super().__init__()
        self.span = token.span
        self.found_type = token.type_
        self.expected = expected

    def to_json(self, source, source_path):
        return {
            "source_path": source_path,
            "error_name": "unexpected_token",
            "line": self.span[1],
            "column": self.span[0],
            "expected": (token.value for token in self.expected),
        }

    def to_alert_message(self, source, source_path):
        quoted_exprs = [f'"{exp.value}"' for exp in self.expected]
        if not self.expected:
            message = "This expression was not formed well."
        elif len(quoted_exprs) == 1:
            message = f"I expected to find {quoted_exprs[0]}"
        else:
            *body, tail = quoted_exprs
            message = f"I expected to find {', '.join(body)} or {tail} here."
        return (message, self.span)

    def to_long_message(self, source, source_path):
        if not self.expected:
            explanation = wrap_text("This expression has an unknown form.")
            return f"{make_pointer(source, self.span)}\n\n{explanation}"
        if len(self.expected) < 4:
            explanation = wrap_text(
                "I expected to find "
                + " or ".join((f'"{exp.value}"' for exp in self.expected))
                + " here."
            )
            return f"{make_pointer(self.span[0], source)}\n\n{explanation}"

        *body, tail = [f'"{exp.value}"' for exp in self.expected]
        explanation = wrap_text(f"I expected to find {', '.join(body)} or {tail} here.")
        return f"{make_pointer(self.span[0], source)}\n\n{explanation}"

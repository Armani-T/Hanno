from enum import auto, Enum
from textwrap import wrap
from typing import Optional, Tuple, TypedDict

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
    OUT_FILE_NOT_FOUND = auto()
    NO_PERMISSION = auto()


class JSONResult(TypedDict, total=False):
    source_path: str
    error_name: str


def relative_pos(absolute_pos: int, source: str) -> Tuple[int, int]:
    """
    Get the column and line number of a character in some source code
    given the position of the character as an offset from the start of
    the source.

    Parameters
    ----------
    source: str
        The source text that the character came from.
    absolute_pos: int
        The position of the character as an offset from the start of
        `source`.

    Returns
    -------
    int * int
        The relative position with the column then the line number.
    """
    cut_source = source[:absolute_pos]
    column = max(((absolute_pos - cut_source.rfind("\n")) - 1), 0)
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
    if source.find("\n", pos) == -1:
        source_line = source[start:]
    else:
        source_line = source[start : source.find("\n", pos)]
    preface = f"{line} |"
    return f"{preface}{source_line}\n{' ' * (len(preface) - 1)}|{'-'* column}^"


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
    ) -> Tuple[str, Optional[int]]:
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
            or the positional data. If the postional data is needed, it
            will be added to the actual message.
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

    __slots__ = ("reason",)

    def __init__(self, reason: CMDErrorReasons):
        super(CMDError, self).__init__()
        self.reason: CMDErrorReasons = reason

    def to_json(self, _, source_path):
        return {"error_name": self.reason.name.lower(), "source_path": source_path}

    def to_alert_message(self, source, source_path):
        message = {
            CMDErrorReasons.OUT_FILE_NOT_FOUND: (
                f'The file "{source_path}" was not found.'
            ),
            CMDErrorReasons.NO_PERMISSION: (
                f'Unable to read the file "{source_path}" we don\'t have the required'
                " permissions."
            ),
        }[self.reason]
        return (message, None)

    def to_long_message(self, source, source_path):
        default_message = (
            "Hasdrubal was unable to read the file due to a fatal internal error."
        )
        message = {
            CMDErrorReasons.OUT_FILE_NOT_FOUND: (
                f'The file "{source_path}" cannot be found, please check if the path'
                " given is correct and whether the file exists."
            ),
            CMDErrorReasons.NO_PERMISSION: (
                f'Hasdrubal was unable to open the file "{source_path}" because it'
                " does not have the required permissions."
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
        return ("A fatal error has occured inside the runtime.", None)

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

    def __init__(self, pos: int, char: str) -> None:
        super().__init__()
        self.pos: int = pos
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
        return (message, self.pos)

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
        return f"{make_pointer(self.pos, source)}\n\n{wrap_text(explanation)}"


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
        explanation = wrap_text(
            f'The file ended before I could finish parsing a "{self.expected}".'
        )
        return f"{make_pointer(len(source) - 1, source)}\n\n{explanation}"

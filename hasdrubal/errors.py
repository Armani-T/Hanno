from textwrap import wrap

from typing import Optional, Tuple, TypedDict

LINE_WIDTH = 87
# NOTE: For some reason, this value has to be off by one. The actual
#  line width is `88` in this case.

wrap_text = lambda string: "\n".join(
    wrap(
        string,
        width=LINE_WIDTH,
        tabsize=4,
        drop_whitespace=False,
        replace_whitespace=False,
    )
)


class JSONResult(TypedDict, total=False):
    source_path: str
    error_name: str


def relative_pos(source: str, absolute_pos: int) -> Tuple[int, int]:
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
        A tuple pair with the relative position in the format
        `(column, line_number)`.
    """
    cut_source = source[:absolute_pos]
    column = max(((absolute_pos - cut_source.rfind("\n")) - 1), 0)
    line = 1 + cut_source.count("\n")
    return column, line


def make_pointer(source: str, pos: int) -> str:
    """
    Make an arrow that points to the offending token in `source`.

    Parameters
    ----------
    source: str
        The source code, we need it because the arrow will point to
        a specific line so that line needs to be printed out.
    pos: int
        The position of the offending token in the source code.

    Returns
    -------
    str
        The source code line with a problem with the arrow that points
        specifically to the offending token.
    """
    start = 1 + source.rfind("\n", 0, pos)
    if source.find("\n", pos) == -1:
        source_line = source[start:]
    else:
        source_line = source[start : source.find("\n", pos)]
    column, lineno = relative_pos(source, pos)
    preface = f"{lineno} |"
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
        column, line = relative_pos(source, len(source) - 1)
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
        return f"{make_pointer(source, self.pos)}\n\n{wrap_text(explanation)}"


class UnexpectedEOFError(HasdrubalError):
    """
    This is an error where the stream of lexer tokens ends in the
    middle of a parser rule.
    """

    def __init__(self, expected: Optional[str] = None) -> None:
        super().__init__()
        self.expected: Optional[str] = expected

    def to_json(self, source, source_path):
        column, line = relative_pos(source, len(source) - 1)
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
        return f"{make_pointer(source, len(source) - 1)}\n\n{explanation}"

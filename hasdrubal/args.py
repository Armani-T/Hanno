from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from sys import stderr, stdout
from typing import Callable, Optional

from errors import (
    CMDError,
    CMDErrorReasons,
    HasdrubalError,
    to_alert_message,
    to_json,
    to_long_message,
)

Reporter = Callable[[HasdrubalError, str, str], str]
Writer = Callable[[str], Optional[int]]


@dataclass(eq=False, frozen=True, repr=False)
class ConfigData:
    """
    All of the options that the user can pass in at the command line.
    """

    file: Optional[Path]
    report_error: Reporter
    encoding: str
    show_ast: bool
    show_help: bool
    show_version: bool
    show_tokens: bool
    show_types: bool
    sort_defs: bool
    write: Writer

    def __or__(self, other):
        if isinstance(other, ConfigData):
            return ConfigData(
                other.file if self.file is None else self.file,
                other.report_error,
                other.encoding if self.encoding == "utf-8" else self.encoding,
                self.show_ast or other.show_ast,
                self.show_help or other.show_help,
                self.show_version or other.show_version,
                self.show_tokens or other.show_tokens,
                self.show_types or other.show_types,
                self.sort_defs and other.sort_defs,
                other.write,
            )
        if isinstance(other, dict):
            return ConfigData(
                other.get("file", self.file) if self.file is None else self.file,
                other.get("report_error", self.report_error),
                other.get("encoding", self.encoding),
                self.show_ast or other.get("show_ast", False),
                self.show_help or other.get("show_help", False),
                self.show_version or other.get("show_version", False),
                self.show_tokens or other.get("show_tokens", False),
                self.show_types or other.get("show_types", False),
                self.sort_defs and other.get("sort_defs", True),
                other.get("write", self.write),
            )
        return NotImplemented


def get_writer(file_path: Optional[str]) -> Writer:
    """
    Use the given file path to generate a writer function for printing
    messages to the user.

    Parameters
    ----------
    file_path: Optional[str]
        The path to the file or stream where messages to the user are
        supposed to go. If it's `None `, then `stdout.write` will be
        returned.

    Raises
    ------
    errors.CMDError
        In case an actual file path is given and it can't be found.

    Returns
    -------
    Callable[[str], Optional[int]]
        A function which takes a `str` message and (probably) does some
        IO with it and returns either an `int` status or `None`.
    """
    if file_path is None or file_path == "stdout":
        return stdout.write
    if file_path == "stderr":
        return stderr.write

    try:
        path = Path(file_path)
        path.touch()
        return path.resolve(strict=True).write_text
    except FileNotFoundError as error:
        raise CMDError(CMDErrorReasons.FILE_NOT_FOUND) from error
    except PermissionError as error:
        raise CMDError(CMDErrorReasons.NO_PERMISSION) from error


def build_config(cmd_args: Namespace) -> ConfigData:
    """
    Convert the argparse namespace into a more usable format.

    Parameters
    ----------
    cmd_args: Namespace
        The arguments directly from argparse.

    Returns
    -------
    ConfigData
        The config data that is actually needed.
    """
    reporter: Reporter = {
        "json": to_json,
        "short": to_alert_message,
        "long": to_long_message,
    }[cmd_args.report_format]

    return ConfigData(
        None if cmd_args.file is None else Path(cmd_args.file),
        reporter,
        cmd_args.encoding,
        cmd_args.show_ast,
        cmd_args.show_help,
        cmd_args.show_version,
        cmd_args.show_tokens,
        cmd_args.show_types,
        cmd_args.sort_defs,
        get_writer(cmd_args.out),
    )


DEFAULT_CONFIG = ConfigData(
    None,
    lambda exc, source, path: exc.to_long_message(source, path),
    "utf-8",
    False,
    False,
    False,
    False,
    False,
    True,
    get_writer(None),
)

parser = ArgumentParser(allow_abbrev=False, add_help=False, prog="hasdrubal")
parser.add_argument(
    "-?",
    "-h",
    "--help",
    action="store_true",
    dest="show_help",
    help="Show this help message and quit.",
)
parser.add_argument(
    "-v",
    "--version",
    action="store_true",
    dest="show_version",
    help="Show the program version number and quit.",
)
parser.add_argument("file", default=None, help="The file to run.", nargs="?")
parser.add_argument(
    "-o",
    "--out",
    action="store",
    default="stdout",
    help=(
        "Where to write the output from running the file. You can also pass in"
        ' "stdout" and "stderr".'
    ),
)
parser.add_argument(
    "-r",
    "--report-fmt",
    "--report-format",
    action="store",
    choices=("json", "long", "short"),
    default="long",
    dest="report_format",
    help="The format of any error message that may arise.",
)
parser.add_argument(
    "-e",
    "--encoding",
    action="store",
    default="utf8",
    help="The encoding of the file.",
)
parser.add_argument(
    "--lex",
    "--lexonly",
    "--lex-only",
    action="store_true",
    dest="show_tokens",
    help="Lex the file and show the resulting tokens (for debugging purposes only).",
)
parser.add_argument(
    "--parse",
    "--parseonly",
    "--parse-only",
    action="store_true",
    dest="show_ast",
    help="Parse the file and show the resulting AST (for debugging purposes only).",
)
parser.add_argument(
    "--type-check",
    "--type-check-only",
    action="store_true",
    dest="show_types",
    help=(
        "Type check the file and show the resulting AST (for debugging purposes only)."
    ),
)
parser.add_argument(
    "--sort-ast",
    "--sort-defs",
    "--sort-definitions",
    action="store_false",
    dest="sort_defs",
    help="Sort expressions in the AST to ensure that definitions come before usages.",
)

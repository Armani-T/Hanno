from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from sys import stderr, stdout
from typing import Callable, Optional, Tuple, Union

from errors import (
    CMDError,
    CMDErrorReasons,
    to_alert_message,
    to_json,
    to_long_message,
)

Reporter = Callable[[Exception, str, str], str]
Writer = Callable[[str], Optional[int]]


@dataclass(eq=False, frozen=True, repr=False)
class ConfigData:
    """
    All of the options that the user can pass in at the command line.
    """

    file: Optional[Path]
    encoding: str
    compress: bool
    expansion_level: int
    out_file: Union[str, Path]
    show_ast: bool
    show_help: bool
    show_version: bool
    show_tokens: bool
    show_types: bool
    sort_defs: bool
    writers: Tuple[Reporter, Writer]
    # NOTE: I have to package them as a pair because otherwise mypy
    #  will think that they are normal methods on the object.

    def __or__(self, other):
        if isinstance(other, ConfigData):
            return ConfigData(
                other.file if self.file is None else self.file,
                other.encoding if self.encoding == "utf-8" else self.encoding,
                self.compress or other.compress,
                max(self.expansion_level, other.expansion_level),
                other.out_file,
                self.show_ast or other.show_ast,
                self.show_help or other.show_help,
                self.show_version or other.show_version,
                self.show_tokens or other.show_tokens,
                self.show_types or other.show_types,
                self.sort_defs or other.sort_defs,
                other.writers,
            )
        if isinstance(other, dict):
            return ConfigData(
                other.get("file", self.file) if self.file is None else self.file,
                other.get("encoding", self.encoding),
                self.compress or other.get("compress", True),
                max(self.expansion_level, other.get("expansion_level", 0)),
                other.get("out_file", self.out_file),
                self.show_ast or other.get("show_ast", False),
                self.show_help or other.get("show_help", False),
                self.show_version or other.get("show_version", False),
                self.show_tokens or other.get("show_tokens", False),
                self.show_types or other.get("show_types", False),
                self.sort_defs or other.get("sort_defs", False),
                other.get("writers", self.writers),
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
        supposed to go. If it's `None `, then `stdout.writer` will be
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
    out_file = (
        Path(cmd_args.out) if cmd_args.out not in ("stdout", "stderr") else cmd_args.out
    )
    return ConfigData(
        None if cmd_args.file is None else Path(cmd_args.file),
        cmd_args.encoding,
        cmd_args.compress,
        cmd_args.expansion_level,
        out_file,
        cmd_args.show_ast,
        cmd_args.show_help,
        cmd_args.show_version,
        cmd_args.show_tokens,
        cmd_args.show_types,
        cmd_args.sort_defs,
        (reporter, get_writer(cmd_args.out)),
    )


DEFAULT_CONFIG = ConfigData(
    None,
    "utf-8",
    True,
    1,
    "stdout",
    False,
    False,
    False,
    False,
    False,
    False,
    (to_long_message, get_writer(None)),
)

parser = ArgumentParser(allow_abbrev=False, add_help=False, prog="hanno")
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
    "--lex-only",
    action="store_true",
    dest="show_tokens",
    help="Lex the file and show the resulting tokens (for debugging purposes only).",
)
parser.add_argument(
    "--parse",
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
    "--sort-defs",
    "--sort-definitions",
    action="store_true",
    dest="sort_defs",
    help="Sort expressions in the AST to ensure that definitions come before usages.",
)
parser.add_argument(
    "--no-compress",
    action="store_false",
    dest="compress",
    help="Compress the bytecode to make it take up less space on disk.",
)
parser.add_argument(
    "--expansion-level",
    "--inline-expansion-level",
    choices=(1, 2, 3),
    default=1,
    dest="expansion_level",
    help="How aggressive the inline expansion should be.",
)

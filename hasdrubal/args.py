from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from sys import stderr, stdout
from typing import Callable, Optional

from errors import CMDError, CMDErrorReasons, HasdrubalError

Reporter = Callable[[HasdrubalError, str, str], str]
Writer = Callable[[str], Optional[int]]


@dataclass(eq=False, frozen=True, repr=False)
class ConfigData:
    """
    All of the options that the user can pass in at the command line.
    """

    file: Optional[Path]
    infer_semicolons: bool
    report_error: Reporter
    source_encoding: str
    show_help: bool
    show_version: bool
    show_tokens: bool
    write: Writer


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
    help="The encoding of the file passed in.",
)
parser.add_argument(
    "-s",
    "--semicolons",
    action="store_true",
    help="Turn off semicolon inference.",
)
parser.add_argument(
    "--lex",
    "--lexonly",
    "--lex-only",
    action="store_true",
    dest="show_tokens",
    help=(
        "Perform lexing on the file, show the resulting tokens and quit (for debugging"
        " purposes only)."
    ),
)


def _get_writer(file_path: str) -> Writer:
    if file_path == "stderr":
        return stderr.write
    if file_path == "stdout":
        return stdout.write

    try:
        path = Path(file_path)
        path.touch()
        return path.resolve(strict=True).write_text
    except FileNotFoundError as error:
        raise CMDError(CMDErrorReasons.OUT_FILE_NOT_FOUND) from error
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
    reporter: Reporter = lambda exc, *args, **kwargs: {
        "json": exc.report_json(*args, **kwargs),
        "short": exc.report_short(*args, **kwargs),
        "long": exc.report_long(*args, **kwargs),
    }[cmd_args.report_format]

    return ConfigData(
        None if cmd_args.file is None else Path(cmd_args.file),
        cmd_args.semicolons,
        reporter,
        cmd_args.encoding,
        cmd_args.show_help,
        cmd_args.show_version,
        cmd_args.show_tokens,
        _get_writer(cmd_args.out),
    )

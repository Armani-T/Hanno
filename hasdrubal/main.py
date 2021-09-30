from sys import exit as sys_exit
from typing import Callable, NoReturn, Union

import errors
import pprint_ as pprint
from args import build_config, ConfigData, parser
from ast_sorter import topological_sort
from lex import infer_eols, lex, normalise_newlines, show_tokens, to_utf8, TokenStream
from log import logger
from parse_ import parse
from type_inferer import infer_types
from type_var_resolver import resolve_type_vars

CURRENT_VERSION = "0.0.1"


def run_code(source: Union[bytes, str], config: ConfigData) -> str:
    """
    This function actually runs the source code given to it.

    Parameters
    ----------
    source: Union[bytes, str]
        The source code to be run. If it is `bytes`, then it will be
        converted first.
    config: ConfigData
        Command line options that can change how the function runs.

    Returns
    -------
    str
        A string representation of the results of computation, whether
        that is an errors message or a message saying that it is done.
    """
    report, _ = config.writers
    to_string: Callable[[Union[bytes, str]], str] = lambda text: (
        text if isinstance(text, str) else to_utf8(text, config.encoding)
    )
    try:
        tokens = infer_eols(lex(normalise_newlines(to_string(source))))
        if config.show_tokens:
            logger.info("Showing tokens.")
            return show_tokens(tokens)

        ast = parse(TokenStream(tokens))
        if config.show_ast:
            logger.info("Showing AST.")
            printer = pprint.ASTPrinter()
            return printer.run(ast)

        ast = resolve_type_vars(ast)
        ast = infer_types(topological_sort(ast) if config.sort_defs else ast)
        if config.show_types:
            logger.info("Showing Typed AST.")
            typed_printer = pprint.TypedASTPrinter()
            return typed_printer.run(ast)

        return ""
    except KeyboardInterrupt:
        return "Program aborted."
    except Exception as err:  # pylint: disable=W0703
        logger.exception("A fatal python error was encountered.", exc_info=True)
        return report(
            err, to_string(source), "" if config.file is None else str(config.file)
        )


def run_file(config: ConfigData) -> int:
    """
    Run the source code found inside a file.

    Parameters
    ----------
    config: ConfigData
        Command line options that can change how the function runs.

    Returns
    -------
    int
        The program exit code.
    """
    report, write = config.writers
    try:
        if config.file is None:
            logger.fatal("A file was not given and it was not asking for a version.")
            write(
                "Please provide a file for the program to run."
                f"\n\n{parser.format_usage()}\n"
            )
            return 64
        source = config.file.resolve(strict=True).read_bytes()
    except PermissionError:
        error = errors.CMDError(errors.CMDErrorReasons.NO_PERMISSION)
        result = write(report(error, "", str(config.file)))
        return 0 if result is None else result
    except FileNotFoundError:
        error = errors.CMDError(errors.CMDErrorReasons.FILE_NOT_FOUND)
        result = write(report(error, "", str(config.file)))
        return 0 if result is None else result
    else:
        write(run_code(source, config))
        return 0


# pylint: disable=C0116
def main() -> NoReturn:
    config = build_config(parser.parse_args())
    _, write = config.writers
    status = 0
    if config.show_help:
        logger.info("Printing the help message.")
        write(parser.format_help())
    elif config.show_version:
        logger.info("Printing the version.")
        write(f"Hasdrubal v{CURRENT_VERSION}\n")
    else:
        status = run_file(config)
    sys_exit(status)

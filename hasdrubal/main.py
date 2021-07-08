from sys import exit as sys_exit
from typing import Callable, NoReturn, Union

from args import build_config, ConfigData, parser
from lex import infer_eols, lex, show_tokens, to_utf8
from log import logger
from parse_ import parse
from pprint_ import PPrinter
import errors

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
    to_string: Callable[[Union[bytes, str]], str] = lambda text: (
        text if isinstance(text, str) else to_utf8(text, config.encoding)
    )
    try:
        tokens = infer_eols(lex(to_string(source)))
        if config.show_tokens:
            return show_tokens(tokens)

        ast = parse(tokens)
        if config.show_ast:
            printer = PPrinter()
            return printer.run(ast)
        return ""
    except errors.HasdrubalError as err:
        return config.report_error(err, to_string(source), str(config.file))
    except KeyboardInterrupt:
        return "Program aborted."
    except Exception as err:  # pylint: disable=W0703
        logger.exception("A fatal python errors was encountered.", exc_info=True)
        return config.report_error(err, to_string(source), str(config.file))


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
    if config.file is None:
        logger.fatal("A file was not given and it was not asking for a version.")
        config.write(
            "Please provide a file for the program to run."
            f"\n\n{parser.format_usage()}\n"
        )
        return 1

    source = config.file.resolve(strict=True).read_bytes()
    config.write(run_code(source, config))
    return 0


# pylint: disable=C0116
def main() -> NoReturn:
    config = build_config(parser.parse_args())
    if config.show_help:
        status = 0
        logger.info("Printing the help message.")
        config.write(parser.format_help())
    elif config.show_version:
        status = 0
        logger.info("Printing the version.")
        config.write(f"Hasdrubal v{CURRENT_VERSION}\n")
    else:
        status = run_file(config)
    sys_exit(status)

from sys import exit as sys_exit
from typing import NoReturn

import errors
from args import build_config, ConfigData, parser
from log import logger
from run import run_code

CURRENT_VERSION = "0.0.1"


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

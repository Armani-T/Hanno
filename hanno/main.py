from sys import exit as sys_exit
from typing import NoReturn

from args import build_config, ConfigData, parser
from log import logger
from run import get_version, run_code
import errors


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
        if config.file.is_dir():
            logger.fatal("A folder was passed into the program instead of a file.")
            raise ValueError()

        source_bytes = config.file.resolve(strict=True).read_bytes()
        out_text = run_code(source_bytes, config)
        write(out_text)
        return 0
    except AttributeError:
        logger.error("No file was passed in to be run.")
        write(
            "Please provide a file for the program to run."
            f"\n\n{parser.format_usage()}\n"
        )
        return 64
    except ValueError:
        write(
            report(
                errors.CMDError(errors.CMDErrorReasons.PATH_IS_FOLDER),
                "",
                str(config.file),
            )
        )
        return 65
    except (PermissionError, FileNotFoundError) as error:
        new_error = errors.CMDError(
            errors.CMDErrorReasons.NO_PERMISSION
            if isinstance(error, PermissionError)
            else errors.CMDErrorReasons.FILE_NOT_FOUND
        )
        write(report(new_error, "", str(config.file)))
        return 66


def main() -> NoReturn:
    config = build_config(parser.parse_args())
    _, write = config.writers
    if config.show_help:
        logger.info("Printing the help message.")
        write(parser.format_help())
        sys_exit(0)
    elif config.show_version:
        logger.info("Printing the version.")
        status, version = get_version()
        write(f"Hanno Version {version}\n")
        sys_exit(status)
    sys_exit(run_file(config))

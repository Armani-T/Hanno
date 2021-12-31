from functools import partial, reduce
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, TypedDict, Union

from args import ConfigData
from lex import infer_eols, lex, normalise_newlines, show_tokens, to_utf8, TokenStream
from log import logger
from parse import parse
from visitors import (
    ast_sorter,
    constant_folder,
    inline_expander,
    type_var_resolver,
)
import pprint_ as pprint
from codegen import compress, simplify, to_bytecode
from type_inference import infer_types
import errors

DEFAULT_FILENAME = "result"
DEFAULT_FILE_EXTENSION = ".livy"

do_nothing = lambda x: x
pipe = partial(reduce, lambda arg, func: func(arg))


# pylint: disable=C0115
class PhaseData(TypedDict):
    after: Iterable[Callable[[Any], Any]]
    before: Iterable[Callable[[Any], Any]]
    main: Callable[[Any], Any]
    on_stop: Callable[[Any], str]
    should_stop: bool


# pylint: disable=C0115
class CompilerPhases(TypedDict):
    lexing: PhaseData
    parsing: PhaseData
    type_checking: PhaseData
    codegen: PhaseData


generate_tasks: Callable[[ConfigData], CompilerPhases]
generate_tasks = lambda config: {
    "lexing": {
        "before": (normalise_newlines,),
        "main": lex,
        "after": (infer_eols,),
        "should_stop": config.show_tokens,
        "on_stop": show_tokens,
    },
    "parsing": {
        "before": (TokenStream,),
        "main": parse,
        "after": (),
        "should_stop": config.show_ast,
        "on_stop": pprint.ASTPrinter().run,
    },
    "type_checking": {
        "before": (
            type_var_resolver.resolve_type_vars,
            ast_sorter.topological_sort if config.sort_defs else do_nothing,
        ),
        "main": infer_types,
        "after": (),
        "should_stop": config.show_types,
        "on_stop": pprint.TypedASTPrinter().run,
    },
    "codegen": {
        "before": (
            simplify,
            partial(inline_expander.expand_inline, level=config.expansion_level),
            constant_folder.fold_constants,
        ),
        "main": to_bytecode,
        "after": (compress if config.compress else do_nothing,),
        "should_stop": False,
        "on_stop": lambda _: "",
    },
}


def build_phase_runner(config: ConfigData) -> Callable[[str, Any], Any]:
    """
    Create the function that will run the different compiler phases.

    Parameters
    ----------
    config: ConfigData
        The program configuration data generated from command line
        flags.

    Returns
    -------
    PhaseRunner
        A function that runs a single compiler phase.
    """
    task_map = generate_tasks(config)

    def inner(phase: str, initial: Any) -> Any:
        tasks = task_map[phase]  # type: ignore
        prepared_value = pipe(tasks["before"], initial)
        main_func = tasks["main"]
        main_value = main_func(prepared_value)
        processed_value = pipe(tasks["after"], main_value)
        return tasks["should_stop"], tasks["on_stop"], processed_value

    return inner


def run_code(source_code: bytes, config: ConfigData) -> str:
    """
    This function actually runs the source code given to it.

    Parameters
    ----------
    source_code: bytes
        The source code to be run as raw bytes from a file.
    config: ConfigData
        Command line options that can change how the function runs.

    Returns
    -------
    str
        A string representation of the results of computation, whether
        that is an errors message or a message saying that it is done.
    """
    report, _ = config.writers
    source_string: str = to_utf8(source_code, config.encoding)
    try:
        source: Any = source_string
        run_phase = build_phase_runner(config)
        for phase in ("lexing", "parsing", "type_checking", "codegen"):
            stop, callback, source = run_phase(phase, source)
            if stop:
                return callback(source)

        if isinstance(source, (bytes, bytearray)):
            write_to_file(source, config)
            return ""
        logger.fatal(
            (
                "Finished going through the phases but the type of source is not "
                "`bytes`, instead it is `type(source)` = %s` so it was not written "
                "to the destination file."
            ),
            source.__class__.__name__,
            stack_info=True,
        )
        raise errors.FatalInternalError()
    except errors.HasdrubalError as error:
        return report(
            error, source_string, "" if config.file is None else str(config.file)
        )


def write_to_file(bytecode: bytes, config: ConfigData) -> int:
    """
    Write a stream of bytecode instructions to an output file so that
    the VM can run them.

    Parameters
    ----------
    bytecode: bytes
        The stream of instructions to be written out.
    config: ConfigData
        Config info that will be used to figure out the output file
        path and report errors.

    Returns
    -------
    int
        Whether the operation was successful or not. `0` means success.
    """
    report, write = config.writers
    try:
        out_file = get_output_file(config.file, config.out_file)
        logger.info("Writing bytecode out to `%s`.", out_file)
        out_file.write_bytes(bytecode)
        return 0
    except PermissionError:
        error = errors.CMDError(errors.CMDErrorReasons.NO_PERMISSION)
        result = write(report(error, "", str(config.file)))
        return 0 if result is None else result
    except FileNotFoundError:
        error = errors.CMDError(errors.CMDErrorReasons.FILE_NOT_FOUND)
        result = write(report(error, "", str(config.file)))
        return 0 if result is None else result


def get_output_file(in_file: Optional[Path], out_file: Union[str, Path]) -> Path:
    """
    Create the output file for writing out bytecode.

    Parameters
    ----------
    in_file: Optional[Path]
        The file that the source code was read from.
    out_file: Union[str, Path]
        The output file that the user has specified for the bytecode
        to be written out to.

    Returns
    -------
    Path
        The output file.

    Notes
    --------
    - Priority will be given to the `out_file` provided it is not
      specified to be `stdout` or `sterr`.
    - The function will create the output file if it doesn't exist
      already.
    """
    if isinstance(out_file, Path):
        out_file.touch()
        return out_file

    if in_file is None or in_file.is_symlink() or in_file.is_socket():
        out_file = Path.cwd() / DEFAULT_FILENAME
    elif in_file.is_file():
        out_file = in_file
    elif in_file.is_dir():
        out_file = in_file / DEFAULT_FILENAME
    else:
        out_file = in_file.cwd() / DEFAULT_FILENAME

    out_file = out_file.with_suffix(DEFAULT_FILE_EXTENSION)
    out_file.touch()
    return out_file

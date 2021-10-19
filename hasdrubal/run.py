from functools import partial, reduce
from pathlib import Path
from typing import Any, Callable, cast, Iterable, TypedDict, TypeVar

from args import ConfigData
from ast_sorter import topological_sort
from codegen import compress, to_bytecode
from lex import infer_eols, lex, normalise_newlines, show_tokens, to_utf8, TokenStream
from log import logger
from parse_ import parse
from pprint_ import ASTPrinter, TypedASTPrinter
from type_inferer import infer_types
from type_var_resolver import resolve_type_vars
import errors

AfterResult = TypeVar("AfterResult")
BeforeResult = TypeVar("BeforeResult")
MainResult = TypeVar("MainResult")

do_nothing = lambda x: x
pipe = partial(reduce, lambda arg, func: func(arg))
to_string: Callable[[str, bytes], str] = lambda encoding, text: (
    text if isinstance(text, str) else to_utf8(text, encoding)
)


class PhaseData(TypedDict):
    after: Iterable[Callable[[MainResult], AfterResult]]
    before: Iterable[Callable[[Any], BeforeResult]]
    main: Callable[[BeforeResult], MainResult]
    on_stop: Callable[[AfterResult], str]
    should_stop: bool


generate_tasks: Callable[[ConfigData], PhaseData] = lambda config: {
    "lexing": {
        "before": (partial(to_string, config.encoding), normalise_newlines),
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
        "on_stop": ASTPrinter().run,
    },
    "type_checking": {
        "before": (
            resolve_type_vars,
            topological_sort if config.sort_defs else do_nothing,
        ),
        "main": infer_types,
        "after": (),
        "should_stop": config.show_types,
        "on_stop": TypedASTPrinter().run,
    },
    "codegen": {
        "before": (),
        "main": to_bytecode,
        "after": (compress if config.compress else do_nothing,),
        "should_stop": False,
        "on_stop": lambda _: "",
    },
}


def build_phase_runner(config: ConfigData):
    task_map = generate_tasks(config)

    def inner(phase: str, initial: Any) -> Any:
        tasks = task_map[phase]
        prepared_value = pipe(tasks["before"], initial)
        main_func = tasks["main"]
        main_value = main_func(prepared_value)
        processed_value = pipe(tasks["after"], main_value)
        return tasks["should_stop"], tasks["on_stop"], processed_value

    return inner


def run_code(source: bytes, config: ConfigData) -> str:
    """
    This function actually runs the source code given to it.

    Parameters
    ----------
    source: bytes
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
    try:
        run_phase = build_phase_runner(config)
        phases = ("lexing", "parsing", "type_checking", "codegen")
        for phase in phases:
            stop, callback, source = run_phase(phase, source)
            if stop:
                return callback(source)

        write_to_file(source, config)
        return ""
    except errors.HasdrubalError as error:
        return report(
            error,
            to_string(config.encoding, source),
            "" if config.file is None else str(config.file),
        )


def write_to_file(bytecode: bytes, config: ConfigData) -> int:
    report, write = config.writers
    try:
        file_path: Path = cast(config.file, Path)
        out_file: Path = file_path.with_suffix(".livy")
        out_file.touch()
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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Generic, Optional, TypeVar, Union

from args import ConfigData
from asts import base, typed
from codegen import simplify, to_bytecode
from errors import CMDError, CMDErrorReasons, HasdrubalError
from format import ASTPrinter, TypedASTPrinter
from lex import infer_eols, lex, normalise_newlines, to_utf8, TokenStream
from log import logger
from parse import parse
from type_inference import infer_types
from visitors import (
    ast_sorter,
    constant_folder,
    inline_expander,
    string_expander,
    type_var_resolver,
)

TVarA = TypeVar("TVarA", covariant=True)
TVarB = TypeVar("TVarB", covariant=True)
TVarC = TypeVar("TVarC", covariant=True)

DEFAULT_FILENAME = "result"
DEFAULT_FILE_EXTENSION = ".livy"


class Result(ABC, Generic[TVarA, TVarB]):
    """
    A type that represents 2 alternate control flow paths that can be
    taken. The 2 paths are its subclasses: `Continue[TVarA]` and
    `Stop[TVarB]`.

    NOTE: This class is an abstract base class so can't be instantiated.
    """

    @abstractmethod
    def map(self, func: Callable[[TVarA], "Result[TVarC]"]) -> "Result[TVarC, TVarB]":
        """
        Call a function on the value contained within, if we are on the
        `Continue` branch.
        """

    @abstractmethod
    def map_with_config(
        self, func: Callable[[TVarA, ConfigData], "Result[TVarC]"], config: ConfigData
    ) -> "Result[TVarC, TVarB]":
        """Same as `map` but also pass in the runtime config data."""

    @abstractmethod
    def get_message(self, default: str) -> str:
        """
        Get the message at the end, if the code has taken that route,
        otherwise return the `default` one.
        """


class Continue(Result[TVarA, str]):
    """
    The control flow path containing values to be passed to the next
    function.
    """

    def __init__(self, value: TVarA) -> None:
        self.value: TVarA = value

    def map(self, func):
        return func(self.value)

    def map_with_config(self, func, config):
        try:
            return func(self.value, config)
        except HasdrubalError as error:
            report, _ = config.writers
            return Stop(report(error, self.value, str(config.file)))

    def get_message(self, default):
        return default


class Stop(Result[Any, str]):
    """
    The control flow path that has reached the end so the value
    contained doesn't change at all.
    """

    def __init__(self, message: str) -> None:
        self.message: str = message

    def map(self, func):
        return self

    def map_with_config(self, func, config):
        return self

    def get_message(self, default):
        return self.message


def run_lexing(source: str, config: ConfigData) -> Result[TokenStream, str]:
    """Perform the lexing portion of the compiler."""
    normalised_source = normalise_newlines(source)
    stream = lex(normalised_source)
    stream = infer_eols(stream)
    return Stop(stream.show()) if config.show_tokens else Continue(stream)


def run_parsing(source: TokenStream, config: ConfigData) -> Result[base.ASTNode, str]:
    """Perform the parsing portion of the compiler."""
    ast = parse(source)
    ast = string_expander.expand_strings(ast)
    ast = type_var_resolver.resolve_type_vars(ast)
    return Stop(ASTPrinter().run(ast)) if config.show_ast else Continue(ast)


def run_type_checking(
    source: base.ASTNode, config: ConfigData
) -> Result[typed.TypedASTNode, str]:
    """Perform the type checking portion of the compiler."""
    typed_ast = infer_types(
        ast_sorter.topological_sort(source) if config.sort_defs else source
    )
    return (
        Stop(TypedASTPrinter().run(typed_ast))
        if config.show_types
        else Continue(typed_ast)
    )


def run_codegen(source: typed.TypedASTNode, config: ConfigData) -> Result[bytes, str]:
    """Perform the codegen portion of the compiler."""
    ast = simplify(source)
    ast = constant_folder.fold_constants(ast)
    ast = inline_expander.expand_inline(ast, config.expansion_level)
    return Continue(to_bytecode(ast, config.compress))


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
    - Priority will be given to the `out_file` provided and it is not
      `stdout` or `sterr`.
    - The function will create the output file if it doesn't exist
      already.
    """
    if isinstance(out_file, Path):
        pass
    elif isinstance(out_file, str):
        out_file = Path(out_file)
    elif in_file.is_file():
        out_file = in_file
    elif in_file.is_dir():
        out_file = in_file / DEFAULT_FILENAME
    else:
        out_file = in_file.cwd() / DEFAULT_FILENAME

    out_file = out_file.with_suffix(DEFAULT_FILE_EXTENSION)
    out_file.touch()
    return out_file


def write_to_file(bytecode: bytes, config: ConfigData) -> bool:
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
    bool
        Whether the operation was successful or not.
    """
    report, write = config.writers
    try:
        out_file = get_output_file(config.file, config.out_file)
        logger.info("Bytecode written out to: %s", out_file)
        out_file.write_bytes(bytecode)
    except PermissionError:
        error = CMDError(CMDErrorReasons.NO_PERMISSION)
        result = write(report(error, "", str(config.file)))
        return result is not None
    except FileNotFoundError:
        error = CMDError(CMDErrorReasons.FILE_NOT_FOUND)
        result = write(report(error, "", str(config.file)))
        return result is not None
    else:
        return True


def run_code(source: bytes, config: ConfigData) -> str:
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
    return (
        Continue(source)
        .map_with_config(
            lambda source, config: to_utf8(source, config.encoding), config
        )
        .map_with_config(run_lexing, config)
        .map_with_config(run_parsing, config)
        .map_with_config(run_type_checking, config)
        .map_with_config(run_codegen, config)
        .map_with_config(write_to_file, config)
        .get_message("")
    )

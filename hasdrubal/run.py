from pathlib import Path
from typing import Optional, Union

from args import ConfigData
from asts import base, typed
from codegen import simplify, to_bytecode
from codegen import compress, simplify, to_bytecode
from errors import CMDError, CMDErrorReasons, HasdrubalError
from format import ASTPrinter, TypedASTPrinter
from lex import infer_eols, lex, normalise_newlines, show_tokens, to_utf8, TokenStream
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

DEFAULT_FILENAME = "result"
DEFAULT_FILE_EXTENSION = ".livy"


class _FakeMessageException(Exception):
    """
    This is not a real exception, it is only used to communicate with
    `run_code` from inside the other `run_*` functions.
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message


def run_lexing(source: str, config: ConfigData) -> TokenStream:
    """Perform the lexing portion of the compiler."""
    normalised = normalise_newlines(source)
    tokens = lex(normalised)
    tokens_with_eols = infer_eols(tokens)
    stream = TokenStream(tokens_with_eols)
    if config.show_tokens:
        raise _FakeMessageException(show_tokens(stream))

    return stream


def run_parsing(source: TokenStream, config: ConfigData) -> base.ASTNode:
    """Perform the parsing portion of the compiler."""
    ast = parse(source)
    expanded_ast = string_expander.expand_strings(ast)
    resolved_ast = type_var_resolver.resolve_type_vars(expanded_ast)
    if config.show_ast:
        printer = ASTPrinter()
        raise _FakeMessageException(printer.run(resolved_ast))
    return resolved_ast


def run_type_checking(source: base.ASTNode, config: ConfigData) -> typed.TypedASTNode:
    """Perform the type checking portion of the compiler."""
    if config.sort_defs:
        source = ast_sorter.topological_sort(source)

    typed_ast = infer_types(source)
    if config.show_types:
        printer = TypedASTPrinter()
        raise _FakeMessageException(printer.run(typed_ast))
    return typed_ast


def run_codegen(source: typed.TypedASTNode, config: ConfigData) -> bytes:
    """Perform the codegen portion of the compiler."""
    simplified_ast = simplify(source)
    folded_ast = constant_folder.fold_constants(simplified_ast)
    expanded_ast = inline_expander.expand_inline(folded_ast, config.expansion_level)
    bytecode = to_bytecode(expanded_ast, config.compress)
    return bytecode


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
    if isinstance(out_file, str):
        out_file = Path(out_file)
    elif isinstance(out_file, Path):
        out_file = out_file  # pylint: disable=W0127
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
    source_code = to_utf8(source, config.encoding)
    try:
        tokens = run_lexing(source_code, config)
        base_ast = run_parsing(tokens, config)
        typed_ast = run_type_checking(base_ast, config)
        bytecode = run_codegen(typed_ast, config)
        write_to_file(bytecode, config)
    except _FakeMessageException as error:
        return error.message
    except HasdrubalError as error:
        report, _ = config.writers
        return report(error, source_code, str(config.file or Path.cwd()))
    else:
        return ""

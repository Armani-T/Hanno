# pylint: disable=C0116
from pathlib import Path
from sys import argv, exit as sys_exit
from typing import Any, Iterator, NoReturn, Sequence

from context import codegen


def decode_file(source: bytes) -> str:
    compression_flag, source = source[:2], source[2:]
    source = decompress(source) if compression_flag == b"\xff\x00" else source
    headers, body_section = get_headers(source)
    func_pool, body_section = get_func_pool(body_section, headers["func_pool_size"])
    str_pool, body_section = get_str_pool(body_section, headers["str_pool_size"])
    instructions = get_instructions(body_section)
    return headers, func_pool, str_pool, instructions


def explain_all(
    headers: dict[str, Any],
    instructions: Iterator[codegen.Instruction],
    func_pool: tuple[int, bytes],
    string_pool: Sequence[str],
) -> str:
    raise NotImplementedError


def main() -> NoReturn:
    exit_code = 1
    try:
        file_contents = Path(argv[1]).read_bytes()
        explanation = explain_all(*decode_file(file_contents))
    except IndexError:
        print("Please pass a Hasdrubal bytecode file as an argument.")
    except FileNotFoundError:
        print(f"File {argv[1]} not found.")
    else:
        exit_code = 0
        print(explanation)
    finally:
        sys_exit(exit_code)


if __name__ == "__main__":
    main()

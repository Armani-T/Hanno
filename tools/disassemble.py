from pathlib import Path
from sys import argv, exit as sys_exit
from typing import Any, Iterator, NoReturn, Sequence

from context import codegen


def decode_file(source: bytes) -> str:
    compression_flag, source = source[:2], source[2:]
    source = decompress(source) if compression_flag == b"\xff\x00" else source
    header_section, body_section = source.split(b"\r\n\r\n\r\n", 1)
    headers = get_headers(header_section)
    return (
        headers,
        get_instruction_stream(body_section),
        get_func_pool(body_section, headers["func_pool_size"]),
        get_string_pool(body_section, headers["string_pool_size"]),
    )


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
        file = Path(argv[1])
        headers, bytecode, func_pool, str_pool = decode_file(file.read_bytes())
        explanation = explain_all(headers, bytecode, func_pool, str_pool)
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

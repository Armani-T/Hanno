# pylint: disable=C0116
from pathlib import Path
from sys import argv, exit as sys_exit
from typing import Any, Iterator, NoReturn, Sequence

from context import codegen


def get_func_pool(source: bytes, pool_size: int) -> tuple[Sequence[bytes], bytes]:
    pool_section, remainder = source[:pool_size], source[pool_size:]
    functions = []
    current_index = 0
    while current_index < pool_size:
        size_bytes = source[current_index : current_index + 4]
        current_index += 4
        function_size = int.from_bytes(size_bytes, codegen.BYTE_ORDER, signed=False)
        end_point = current_index + function_size
        functions.append(source[current_index:end_point])
        current_index = end_point
    return functions, remainder


def get_headers(source: bytes) -> tuple[dict[str, Any], bytes]:
    func_pool_size = int.from_bytes(source[6:10], codegen.BYTE_ORDER, signed=False)
    str_pool_size = int.from_bytes(source[13:17], codegen.BYTE_ORDER, signed=False)
    stream_size = int.from_bytes(source[20:24], codegen.BYTE_ORDER, signed=False)
    encoding = source[27:43].rstrip(b"\x00").decode("ASCII")
    remainder = source[44:]
    if remainder.startswith(codegen.SECTION_SEP):
        remainder = remainder[len(codegen.SECTION_SEP) :]
        headers = {
            "lib_mode": source[2] == 0xFF,
            "func_pool_size": func_pool_size,
            "str_pool_size": str_pool_size,
            "stream_size": stream_size,
            "encoding": encoding,
        }
        return headers, remainder
    raise ValueError(
        "The bytecode is in an invalid format. "
        "An invalid separator was found between the headers and the func pool."
    )


def decompress(source: bytes) -> bytes:
    pieces = []
    current_index = 0
    current_chunk = source[current_index : current_index + 2]
    while len(current_chunk) == 2:
        pieces.append(bytes([current_chunk[1]] * current_chunk[0]))
        current_index += 2
        current_chunk = source[current_index : current_index + 2]

    if current_chunk:
        pieces.append(current_chunk)
    return b"".join(pieces)


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

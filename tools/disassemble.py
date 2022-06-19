from operator import methodcaller
from pathlib import Path
from sys import argv, exit as sys_exit
from typing import Any, Callable, Iterable, Iterator, NoReturn, Sequence, TypeVar

from context import codegen

TV = TypeVar("TV", covariant=True)

show_str_pool: Callable[[Iterable[str]], str]
show_str_pool = lambda str_pool: "\n".join(map(repr, str_pool))


def get_int_value(sign: int, value: bytes) -> int:
    negate, over_4_bytes = {
        0xFF: (True, True),
        0xF0: (True, False),
        0x0F: (False, True),
        0x00: (False, False),
    }[sign]
    value = value if over_4_bytes else value[:4]
    abs_value = int.from_bytes(value, codegen.BYTE_ORDER, signed=False)
    return -abs_value if negate else abs_value


def get_float_value(sign: int, value: bytes) -> float:
    negate_value, negate_exponent = {
        0xFF: (True, True),
        0xF0: (True, False),
        0x0F: (False, True),
        0x00: (False, False),
    }[sign]
    abs_base = float(int.from_bytes(value[:4], codegen.BYTE_ORDER, signed=False))
    abs_exponent = int.from_bytes(value[4:], codegen.BYTE_ORDER, signed=False)
    exponent = -abs_exponent if negate_exponent else abs_exponent
    value = float(abs_base) ** exponent
    return -value if negate_value else value


def get_name_args(arg_space: bytes) -> tuple[int, int]:
    depth_section, index_section = arg_space[:3], arg_space[3:]
    return (
        int.from_bytes(depth_section, codegen.BYTE_ORDER, signed=False),
        int.from_bytes(index_section, codegen.BYTE_ORDER, signed=False),
    )


def get_op_args(opcode: int, arg_section: bytes) -> tuple[Any, ...]:
    if opcode == codegen.OpCodes.LOAD_BOOL:
        return (arg_section[0] == 0xFF,)
    if opcode == codegen.OpCodes.LOAD_INT:
        return (get_int_value(arg_section[0], arg_section[1:]),)
    if opcode == codegen.OpCodes.LOAD_FLOAT:
        return (get_float_value(arg_section[0], arg_section[1:]),)
    if opcode == codegen.OpCodes.BUILD_LIST:
        return (int.from_bytes(arg_section[:4], codegen.BYTE_ORDER, signed=False),)
    if opcode in (
        codegen.OpCodes.APPLY,
        codegen.OpCodes.NATIVE,
        codegen.OpCodes.BUILD_TUPLE,
    ):
        return (int.from_bytes(arg_section[:1], codegen.BYTE_ORDER, signed=False),)
    if opcode in (codegen.OpCodes.LOAD_NAME, codegen.OpCodes.STORE_NAME):
        return get_name_args(arg_section)
    return (int.from_bytes(arg_section, codegen.BYTE_ORDER, signed=False),)


def get_instructions(source: bytes) -> Iterator[codegen.Instruction]:
    current_index = 0
    current_chunk = source[current_index : current_index + 8]
    while current_chunk:
        opcode, op_args = current_chunk[0], current_chunk[1:]
        yield codegen.Instruction(
            codegen.OpCodes(opcode),
            get_op_args(opcode, op_args),
        )
        current_chunk = source[current_index : current_index + 8]


def get_pool(
    source: bytes, pool_size: int, transform: Callable[[bytes], TV]
) -> tuple[Sequence[TV], bytes]:
    pool_section, remainder = source[:pool_size], source[pool_size:]
    sections = []
    current_index = 0
    while current_index < pool_size:
        size_bytes = source[current_index : current_index + 4]
        current_index += 4
        size = int.from_bytes(size_bytes, codegen.BYTE_ORDER, signed=False)
        section = transform(source[current_index : (current_index + size)])
        sections.append(section)
        current_index += size
    return sections, remainder


def get_headers(source: bytes) -> tuple[dict[str, Any], bytes]:
    func_pool_size = int.from_bytes(source[6:10], codegen.BYTE_ORDER, signed=False)
    str_pool_size = int.from_bytes(source[13:17], codegen.BYTE_ORDER, signed=False)
    stream_size = int.from_bytes(source[20:24], codegen.BYTE_ORDER, signed=False)
    encoding = source[27:43].rstrip(b"\x00").decode("ASCII")
    headers = {
        "lib_mode": source[2] == 0xFF,
        "func_pool_size": func_pool_size,
        "str_pool_size": str_pool_size,
        "stream_size": stream_size,
        "encoding": encoding,
    }
    return headers, source[43:]


def remove_barrier(source: bytes) -> bytes:
    if source.startswith(codegen.SECTION_SEP):
        return source[len(codegen.SECTION_SEP) :]
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


def decode_file(
    source: bytes,
) -> tuple[
    dict[str, Any], Sequence[bytes], Sequence[str], Iterator[codegen.Instruction]
]:
    compression_flag, source = source[:2], source[2:]
    source = decompress(source) if compression_flag == b"\xff\x00" else source
    headers, body_section = get_headers(source)
    func_pool, body_section = get_pool(
        remove_barrier(body_section),
        headers["func_pool_size"],
        lambda x: x,
    )
    str_pool, body_section = get_pool(
        remove_barrier(body_section),
        headers["str_pool_size"],
        methodcaller("decode", codegen.STRING_ENCODING),
    )
    instructions = get_instructions(remove_barrier(body_section))
    return headers, func_pool, str_pool, instructions


def show_instructions(instructions: Iterable[codegen.Instruction]) -> str:
    def inner(opcode, operands):
        if opcode in (codegen.OpCodes.LOAD_NAME, codegen.OpCodes.STORE_NAME):
            return f"depth = {operands[0]}, index = {operands[1]}"
        return repr(operands[0])

    return "\n".join(
        f"{instr.opcode.name}( {inner(instr.opcode, instr.operands)} )"
        for instr in instructions
    )


def show_func_pool(func_pool: Iterable[bytes]) -> str:
    functions = []
    for index, bytecode in enumerate(func_pool):
        body = show_instructions(get_instructions(bytecode))
        full = f"Function object #{index}:\n{body}"
        full = full.replace("\n", "\n    ")
        functions.append(full)
    return "\n\n".join(functions)


def show_headers(headers: dict[str, Any]) -> str:
    return "\n".join(
        (
            f"Library Mode:            {'Y' if headers['lib_mode'] else 'N'}",
            f"Func Pool Size:          {headers['func_pool_size']} bytes",
            f"String Pool Size:        {headers['func_pool_size']} bytes",
            f"String Encoding:         {headers['encoding']}",
            f"Instruction Stream Size: {headers['stream_size']} bytes",
        )
    )


def show_all(
    headers: dict[str, Any],
    instructions: Iterator[codegen.Instruction],
    func_pool: tuple[int, bytes],
    string_pool: Sequence[str],
) -> str:
    return "\n\n\n".join(
        (
            show_headers(headers),
            show_str_pool(string_pool),
            show_func_pool(func_pool),
            "" if headers["lib_mode"] else show_instructions(instructions),
        )
    )


def main() -> NoReturn:
    exit_code = 1
    try:
        file_contents = Path(argv[1]).read_bytes()
        explanation = show_all(*decode_file(file_contents))
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

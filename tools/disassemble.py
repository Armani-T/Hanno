from pathlib import Path
from sys import argv, exit as sys_exit
from typing import Any, Callable, Iterable, Iterator, NoReturn, Sequence, TypeVar

from context import codegen

TV = TypeVar("TV", covariant=True)

show_str_pool: Callable[[Iterable[str]], str]
show_str_pool = lambda str_pool: "\n".join(map(repr, str_pool))
split = lambda string, index: (string[:index], string[index:])


def get_int_value(sign: int, value: bytes) -> int:
    sign_modifier = -1 if sign >= 0xF0 else +1
    value = value if sign % 10 else value[:4]
    abs_value = int.from_bytes(value, codegen.BYTE_ORDER, signed=False)
    return sign_modifier * abs_value


def get_float_value(sign: int, value: bytes) -> float:
    base_sign = -1 if sign >= 0xF0 else +1
    exp_sign = -1 if sign % 10 else +1
    abs_base = float(int.from_bytes(value[:4], codegen.BYTE_ORDER, signed=False))
    abs_exp = int.from_bytes(value[4:], codegen.BYTE_ORDER, signed=False)
    return base_sign * (abs_base ** (exp_sign * abs_exp))


def get_name_args(arg_space: bytes) -> tuple[int, int]:
    depth_section, index_section = split(arg_space, 3)
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


def read_pool(source: bytes) -> Sequence[bytes]:
    pool_items = []
    while source:
        size_bytes, source = source[:4], source[4:]
        item_size = int.from_bytes(size_bytes, codegen.BYTE_ORDER, signed=False)
        item, source = source[:item_size], source[item_size:]
        pool_items.append(item)
    return pool_items


def read_headers(source: bytes) -> tuple[dict[str, Any], bytes]:
    func_pool_size = int.from_bytes(source[6:10], codegen.BYTE_ORDER, signed=False)
    str_pool_size = int.from_bytes(source[13:17], codegen.BYTE_ORDER, signed=False)
    return {
        "lib_mode": source[2] == 0xFF,
        "func_pool_size": func_pool_size,
        "str_pool_size": str_pool_size,
        "stream_size": int.from_bytes(source[20:24], codegen.BYTE_ORDER, signed=False),
        "encoding": source[27:43].rstrip(b"\x00").decode("ASCII"),
    }


def remove_barrier(source: bytes) -> bytes:
    if source.startswith(codegen.SECTION_SEP):
        return source.lstrip(codegen.SECTION_SEP)
    raise ValueError("Invalid separator found! This bytecode is in an invalid format.")


def decompress(source: bytes) -> bytes:
    pieces = []
    current_index = 0
    current_chunk = source[current_index : current_index + 2]
    while len(current_chunk) == 2:
        pieces.append(bytes([current_chunk[1]] * current_chunk[0]))
        current_index += 2
        current_chunk = source[current_index : current_index + 2]
    pieces.append(current_chunk)
    return b"".join(pieces)


def decode_file(
    source: bytes,
) -> tuple[
    dict[str, Any], Sequence[bytes], Sequence[str], Iterator[codegen.Instruction]
]:
    compression_flag, source = split(source, 2)
    source = decompress(source) if compression_flag == b"\xff\x00" else source
    header_source, source = split(source, 43)
    headers = read_headers(header_source)
    func_source, source = split(remove_barrier(source), headers["func_pool_size"])
    str_source, source = split(remove_barrier(source), headers["str_pool_size"])
    return (
        headers,
        read_pool(func_source),
        (string.decode(codegen.STRING_ENCODING) for string in read_pool(str_source)),
        get_instructions(remove_barrier(source)),
    )


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
            "Headers:",
            f"Function Pool Size (bytes): {headers['func_pool_size']}",
            f"String Encoding:            {headers['encoding']}",
            f"String Pool Size (bytes):   {headers['func_pool_size']}",
            f"Instruction Stream Size:    {headers['stream_size']}",
            f"Library Mode:               {'ON' if headers['lib_mode'] else 'OFF'}",
        )
    )


def main() -> NoReturn:
    exit_code = 1
    try:
        file_contents = Path(argv[1]).read_bytes()
        headers, string_pool, func_pool, instructions = decode_file(file_contents)
        explanation = "\n\n\n".join(
            (
                show_headers(headers),
                show_str_pool(string_pool),
                show_func_pool(func_pool),
                "" if headers["lib_mode"] else show_instructions(instructions),
            )
        )
    except IndexError:
        print("Please pass a Hasdrubal bytecode file as an argument.")
    except FileNotFoundError:
        print(f'"{argv[1]}" has not been found.')
    except ValueError as error:
        print(error.args[0])
    else:
        print(explanation)
        exit_code = 0
    finally:
        sys_exit(exit_code)


if __name__ == "__main__":
    main()

#! usr/bin/env python3
from pathlib import Path
from sys import argv, exit as sys_exit
from typing import Any, Iterable, Iterator, NoReturn, Sequence, TypeVar

from context import codegen

TV = TypeVar("TV", covariant=True)

split = lambda string, index: (string[:index], string[index:])


def get_int_value(sign: int, value: bytes) -> int:
    sign_modifier = -1 if sign >= 0xF0 else +1
    value = value if sign % 10 else value[:4]
    abs_value = int.from_bytes(value, codegen.BYTE_ORDER, signed=False)
    return sign_modifier * abs_value


def get_float_value(value: bytes) -> float:
    base = float(int.from_bytes(value[:5], codegen.BYTE_ORDER, signed=True))
    exponent = float(int.from_bytes(value[5:], codegen.BYTE_ORDER, signed=True))
    return base**exponent


def get_op_args(opcode: codegen.OpCodes, arg_section: bytes) -> tuple[Any, ...]:
    if opcode == codegen.OpCodes.LOAD_BOOL:
        return (arg_section[0] == 0xFF,)
    if opcode == codegen.OpCodes.LOAD_INT:
        return (int.from_bytes(arg_section, codegen.BYTE_ORDER, signed=True),)
    if opcode == codegen.OpCodes.LOAD_FLOAT:
        return (get_float_value(arg_section),)
    if opcode == codegen.OpCodes.NATIVE:
        return (arg_section[0],)
    if opcode == codegen.OpCodes.LOAD_NAME:
        return (
            int.from_bytes(arg_section[:3], codegen.BYTE_ORDER, signed=False),
            int.from_bytes(arg_section[3:], codegen.BYTE_ORDER, signed=False),
        )
    if opcode in (
        codegen.OpCodes.APPLY,
        codegen.OpCodes.BUILD_PAIR,
        codegen.OpCodes.LOAD_UNIT,
    ):
        return ()
    return (int.from_bytes(arg_section, codegen.BYTE_ORDER, signed=False),)


def get_instructions(source: bytes) -> Iterator[codegen.Instruction]:
    index = 0
    while chunk := source[index : index + 8]:
        opcode = codegen.OpCodes(chunk[0])
        yield codegen.Instruction(opcode, get_op_args(opcode, chunk[1:]))
        index += 8


def read_pool(source: bytes) -> Sequence[bytes]:
    pool_items = []
    while source:
        size_bytes, source = source[:4], source[4:]
        item_size = int.from_bytes(size_bytes, codegen.BYTE_ORDER, signed=False)
        item, source = source[:item_size], source[item_size:]
        pool_items.append(item)
    return pool_items


def read_headers(source: bytes) -> tuple[dict[str, Any], bytes]:
    func_pool_size = int.from_bytes(source[5:9], codegen.BYTE_ORDER, signed=False)
    str_pool_size = int.from_bytes(source[11:15], codegen.BYTE_ORDER, signed=False)
    return {
        "lib_mode": bool(source[2]),
        "func_pool_size": func_pool_size,
        "str_pool_size": str_pool_size,
        "stream_size": int.from_bytes(source[17:21], codegen.BYTE_ORDER, signed=False),
        "encoding": source[23:35].rstrip(b"\x00").decode("ASCII"),
    }


def decompress(source: bytes) -> bytes:
    pieces = []
    index = 0
    chunk = source[index : index + 2]
    while len(chunk) == 2:
        pieces.append(bytes([chunk[1]] * chunk[0]))
        index += 2
        chunk = source[index : index + 2]
    pieces.append(chunk)
    return b"".join(pieces)


def decode_file(
    source: bytes,
) -> tuple[
    dict[str, Any], Sequence[bytes], Sequence[str], Iterator[codegen.Instruction]
]:
    compress_flag, source = split(source, 2)
    source = decompress(source) if compress_flag == b"C\xFF" else source
    header_source, source = split(source, 35)
    if not source.startswith(b"\xFF" * 3):
        raise ValueError("This bytecode is in an invalid format.")

    headers = read_headers(header_source)
    func_source, source = split(source[3:], headers["func_pool_size"])
    str_source, source = split(source, headers["str_pool_size"])
    return (
        headers,
        read_pool(func_source),
        [string.decode(codegen.STRING_ENCODING) for string in read_pool(str_source)],
        get_instructions(source),
    )


def show_operand(opcode, operands):
    if opcode == codegen.OpCodes.LOAD_NAME:
        return f"( depth = {operands[0]}, index = {operands[1]} )"
    if opcode in (
        codegen.OpCodes.APPLY,
        codegen.OpCodes.BUILD_PAIR,
        codegen.OpCodes.LOAD_UNIT,
    ):
        return ""
    return f"( {repr(operands[0])} )"


def show_instructions(
    instructions: Iterable[codegen.Instruction], indent: int = 0
) -> str:
    return ("\n" + "\t" * indent).join(
        f"{instr.opcode.name}{show_operand(instr.opcode, instr.operands)}"
        for instr in instructions
    )


def show_func_pool(func_pool: Iterable[bytes]) -> str:
    show_body = lambda code: show_instructions(get_instructions(code), indent=1)
    return "\n".join(
        f"Function object #{index}:\n\t{show_body(bytecode)}"
        for index, bytecode in enumerate(func_pool)
    )


def show_headers(headers: dict[str, Any]) -> str:
    return (
        "Headers\n"
        "-------\n"
        f"Library Mode:            {'ON' if headers['lib_mode'] else 'OFF'}\n"
        f"String Encoding:         {headers['encoding']}\n"
        f"Function Pool Size:      {headers['func_pool_size']} bytes\n"
        f"String Pool Size:        {headers['func_pool_size']} bytes\n"
        f"Instruction Stream Size: {headers['stream_size']} bytes"
    )


def main() -> NoReturn:
    try:
        if len(argv) == 1:
            print("Please pass in a Hanno bytecode file.")
            sys_exit(1)

        file_contents = Path(argv[1]).read_bytes()
        headers, func_pool, string_pool, instructions = decode_file(file_contents)
        print(show_headers(headers), "\n")
        print(show_func_pool(func_pool), "\n")
        if not headers["lib_mode"]:
            print(show_instructions(instructions))
        sys_exit(0)
    except FileNotFoundError:
        print(f'"{argv[1]}" has not been found.')
        sys_exit(1)


if __name__ == "__main__":
    main()

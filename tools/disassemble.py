#! usr/bin/env python3
from pathlib import Path
from sys import argv, exit as sys_exit
from typing import Iterable, Literal, NamedTuple

from context import codegen

ByteOrder = Literal["little", "big"]
Header = NamedTuple(
    "Header", byte_order=ByteOrder, func_pool=int, str_pool=int, encoding=str
)

split = lambda string, index: (string[:index], string[index:])


def get_int_value(sign: int, value: bytes, byte_order: ByteOrder) -> int:
    sign_modifier = -1 if sign >= 0xF0 else +1
    value = value if sign % 10 else value[:4]
    abs_value = int.from_bytes(value, byte_order, signed=False)
    return sign_modifier * abs_value


def get_float_value(value: bytes, byte_order: ByteOrder) -> float:
    base = float(int.from_bytes(value[:5], byte_order, signed=True))
    exponent = float(int.from_bytes(value[5:], byte_order, signed=True))
    return base**exponent


def get_op_args(
    opcode: codegen.OpCodes, arg_section: bytes, byte_order: ByteOrder
) -> tuple[object, ...]:
    if opcode == codegen.OpCodes.LOAD_BOOL:
        return (arg_section[0] == 0xFF,)
    if opcode == codegen.OpCodes.LOAD_INT:
        return (int.from_bytes(arg_section, byte_order, signed=True),)
    if opcode == codegen.OpCodes.LOAD_FLOAT:
        return (get_float_value(arg_section, byte_order),)
    if opcode == codegen.OpCodes.NATIVE:
        return (arg_section[0],)
    if opcode in (codegen.OpCodes.LOAD_NAME, codegen.OpCodes.STORE_NAME):
        return (
            int.from_bytes(arg_section[:3], byte_order, signed=False),
            int.from_bytes(arg_section[3:], byte_order, signed=False),
        )
    if opcode in (
        codegen.OpCodes.APPLY,
        codegen.OpCodes.BUILD_PAIR,
        codegen.OpCodes.LOAD_UNIT,
    ):
        return ()
    return (int.from_bytes(arg_section, byte_order, signed=False),)


def get_instructions(
    source: bytes, byte_order: ByteOrder
) -> Iterable[codegen.Instruction]:
    index = 0
    while chunk := source[index : index + 8]:
        opcode = codegen.OpCodes(chunk[0])
        yield codegen.Instruction(opcode, get_op_args(opcode, chunk[1:], byte_order))
        index += 8


def read_pool(source: bytes, byte_order: ByteOrder) -> Iterable[bytes]:
    pool_items = []
    while source:
        size_bytes, source = source[:4], source[4:]
        item_size = int.from_bytes(size_bytes, byte_order, signed=False)
        item, source = source[:item_size], source[item_size:]
        pool_items.append(item)
    return pool_items


def read_headers(source: bytes) -> Header:
    error_site = (
        "byte order"
        if source[0] != 79
        else (
            "pool size"
            if source[2] != 70 or source[7] != 83
            else "string encoding" if source[12] != 69 else None
        )
    )
    if error_site is not None:
        raise ValueError(f"Cannot read {error_site} from bytecode headers.")

    byte_order: ByteOrder = "big" if source[1] else "little"
    return Header(
        byte_order,
        int.from_bytes(source[3:7], byte_order, signed=False),
        int.from_bytes(source[8:12], byte_order, signed=False),
        source[13:].rstrip(b"\x00").decode("ASCII"),
    )


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
) -> tuple[Header, Iterable[bytes], Iterable[str], Iterable[codegen.Instruction]]:
    compression, source = split(source, 2)
    if compression == b"C\xFF":
        source = decompress(source)
    elif compression != b"C\x00":
        raise ValueError("This file cannot be read as it has an invalid header format")

    header_section, source = split(source, 24)
    headers = read_headers(header_section)
    func_section, source = split(source, headers.func_pool)
    str_section, source = split(source, headers.str_pool)
    return (
        headers,
        read_pool(func_section, headers.byte_order),
        [
            string.decode(headers.encoding)
            for string in read_pool(str_section, headers.byte_order)
        ],
        get_instructions(source, headers.byte_order),
    )


def show_operand(opcode, operands):
    if opcode in (codegen.OpCodes.LOAD_NAME, codegen.OpCodes.STORE_NAME):
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


def show_func_pool(func_pool: Iterable[bytes], byte_order: ByteOrder) -> str:
    show_body = lambda code: show_instructions(
        get_instructions(code, byte_order), indent=1
    )
    return "\n".join(
        f"Function object #{index}:\n\t{show_body(bytecode)}"
        for index, bytecode in enumerate(func_pool)
    )


def show_headers(headers: Header) -> str:
    return (
        "Headers\n-------\n"
        f"Byte Order:         {headers.byte_order}\n"
        f"Function Pool Size: {headers.func_pool} bytes\n"
        f"String Pool Size:   {headers.str_pool} bytes\n"
        f"String Encoding:    {headers.encoding}"
    )


def main():
    try:
        if len(argv) == 1:
            print("Please pass in a Hanno bytecode file.")
            sys_exit(1)

        file_contents = Path(argv[1]).read_bytes()
        headers, func_pool, string_pool, instructions = decode_file(file_contents)
        print(show_headers(headers), "\n")
        print(show_func_pool(func_pool, headers.byte_order), "\n")
        print(show_instructions(instructions))
        sys_exit(0)
    except FileNotFoundError:
        print(f'"{argv[1]}" has not been found.')
        sys_exit(1)


if __name__ == "__main__":
    main()

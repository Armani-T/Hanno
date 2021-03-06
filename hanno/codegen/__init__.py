from typing import Literal

BYTE_ORDER: Literal["big"] = "big"

from .compressor import compress, generate_lengths, rebuild_stream
from .main import (
    encode_instructions,
    encode_pool,
    encode_operands,
    generate_header,
    Instruction,
    InstructionGenerator,
    OpCodes,
    SECTION_SEP,
    STRING_ENCODING,
    to_bytecode,
)
from .simplifier import simplify

__all__ = (
    "BYTE_ORDER",
    "compress",
    "encode_instructions",
    "encode_pool",
    "encode_operands",
    "generate_header",
    "generate_lengths",
    "Instruction",
    "InstructionGenerator",
    "OpCodes",
    "rebuild_stream",
    "SECTION_SEP",
    "simplify",
    "STRING_ENCODING",
    "to_bytecode",
)

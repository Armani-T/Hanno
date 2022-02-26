from pathlib import Path
from sys import argv, exit
from typing import Iterator, NoReturn

from context import codegen


def decode_file(source: bytes) -> str:
    ...


def explain_all(instructions: Iterator[codegen.Instruction]) -> str:
    ...


def main() -> NoReturn:
    if len(argv) > 1:
        file = Path(argv[1])
        bytecode = decode_file(file.read_bytes() if file.exists() else b"")
        print(explain_all(bytecode))
    exit(0)


if __name__ == "__main__":
    main()

from typing import Dict, Generic, Iterator, Optional, Protocol, Tuple, TypeVar

from ast_.type_nodes import (
    FuncType,
    GenericType,
    Type,
    TypeScheme,
    TypeVar as ASTTypeVar,
)
from ast_.base_ast import Name
from errors import UndefinedNameError

ValType = TypeVar("ValType")


class _HasValueAttr(Protocol):
    value: str


# pylint: disable=R0903
class Scope(Generic[ValType]):
    """
    A mapping of all defined names to their values.

    Attributes
    ----------
    _data: Dict[str, ASTNode]
        A `dict` containing those names in string form and their values
        without the values being evaluated.
    parent: Optional[Scope]
        A scope that wraps around `self` and can be requested for
        names that were defined before `self` was made.
    """

    def __init__(self, parent: Optional["Scope"]) -> None:
        self._data: Dict[str, ValType] = {}
        self.parent: Optional[Scope] = parent

    def __bool__(self) -> bool:
        return bool(self._data) and self.parent is not None

    def __contains__(self, name: _HasValueAttr) -> bool:
        return name.value in self._data or (
            self.parent is not None and name in self.parent
        )

    def __delitem__(self, name: _HasValueAttr) -> None:
        if name in self:
            del self._data[name.value]
        elif self.parent is not None:
            del self.parent[name]

    def __iter__(self) -> Iterator[Tuple[str, ValType]]:
        for key, value in self._data.items():
            yield (key, value)

    def __getitem__(self, name: _HasValueAttr) -> ValType:
        if name.value in self._data:
            return self._data[name.value]
        if self.parent is not None:
            return self.parent[name]
        raise UndefinedNameError(name)

    def __setitem__(self, name: _HasValueAttr, value: ValType) -> None:
        if name in self and self.parent is not None:
            self.parent[name] = value
        else:
            self._data[name.value] = value


DEFAULT_OPERATOR_TYPES: Scope[Type] = Scope(None)
DEFAULT_OPERATOR_TYPES[Name((0, 3), "and")] = FuncType(
    (5, 25),
    GenericType((5, 9), Name((5, 9), "Bool")),
    FuncType(
        (13, 25),
        GenericType((13, 17), Name((13, 17), "Bool")),
        GenericType((21, 25), Name((21, 25), "Bool")),
    ),
)
DEFAULT_OPERATOR_TYPES[Name((26, 28), "or")] = FuncType(
    (30, 50),
    GenericType((30, 34), Name((30, 34), "Bool")),
    FuncType(
        (38, 50),
        GenericType((38, 42), Name((38, 42), "Bool")),
        GenericType((46, 50), Name((46, 50), "Bool")),
    ),
)
DEFAULT_OPERATOR_TYPES[Name((51, 54), "not")] = FuncType(
    (56, 68),
    GenericType((56, 60), Name((56, 60), "Bool")),
    GenericType((64, 68), Name((64, 68), "Bool")),
)
DEFAULT_OPERATOR_TYPES[Name((304, 305), "~")] = TypeScheme(
    FuncType(
        (307, 325),
        ASTTypeVar((307, 308), "x"),
        ASTTypeVar((324, 325), "x"),
    ),
    {ASTTypeVar((307, 308), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((69, 70), "=")] = TypeScheme(
    FuncType(
        (72, 86),
        ASTTypeVar((72, 73), "x"),
        FuncType(
            (77, 86),
            ASTTypeVar((77, 78), "x"),
            GenericType((82, 86), Name((82, 86), "Bool")),
        ),
    ),
    {ASTTypeVar((72, 73), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((87, 89), "/=")] = TypeScheme(
    FuncType(
        (91, 105),
        ASTTypeVar((91, 92), "x"),
        FuncType(
            (96, 105),
            ASTTypeVar((96, 97), "x"),
            GenericType((101, 105), Name((101, 105), "Bool")),
        ),
    ),
    {ASTTypeVar((91, 92), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((106, 107), ">")] = TypeScheme(
    FuncType(
        (109, 123),
        ASTTypeVar((109, 110), "x"),
        FuncType(
            (114, 123),
            ASTTypeVar((114, 115), "x"),
            GenericType((119, 123), Name((119, 123), "Bool")),
        ),
    ),
    {ASTTypeVar((109, 110), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((124, 125), "<")] = TypeScheme(
    FuncType(
        (127, 141),
        ASTTypeVar((127, 128), "x"),
        FuncType(
            (132, 141),
            ASTTypeVar((132, 133), "x"),
            GenericType((137, 141), Name((137, 141), "Bool")),
        ),
    ),
    {ASTTypeVar((127, 128), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((142, 144), ">=")] = TypeScheme(
    FuncType(
        (146, 160),
        ASTTypeVar((146, 147), "x"),
        FuncType(
            (151, 160),
            ASTTypeVar((151, 152), "x"),
            GenericType((156, 160), Name((156, 160), "Bool")),
        ),
    ),
    {ASTTypeVar((146, 147), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((161, 163), "<=")] = TypeScheme(
    FuncType(
        (165, 179),
        ASTTypeVar((165, 166), "x"),
        FuncType(
            (170, 179),
            ASTTypeVar((170, 171), "x"),
            GenericType((175, 179), Name((175, 179), "Bool")),
        ),
    ),
    {ASTTypeVar((165, 166), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((180, 181), "+")] = TypeScheme(
    FuncType(
        (183, 194),
        ASTTypeVar((183, 184), "x"),
        FuncType(
            (188, 194),
            ASTTypeVar((188, 189), "x"),
            ASTTypeVar((193, 194), "x"),
        ),
    ),
    {ASTTypeVar((183, 184), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((195, 196), "-")] = TypeScheme(
    FuncType(
        (198, 209),
        ASTTypeVar((198, 199), "x"),
        FuncType(
            (203, 209),
            ASTTypeVar((203, 204), "x"),
            ASTTypeVar((208, 209), "x"),
        ),
    ),
    {ASTTypeVar((198, 199), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((210, 212), "<>")] = TypeScheme(
    FuncType(
        (214, 243),
        GenericType(
            (214, 221), Name((214, 218), "List"), (ASTTypeVar((219, 220), "x"),)
        ),
        FuncType(
            (225, 243),
            GenericType(
                (225, 232), Name((225, 229), "List"), (ASTTypeVar((230, 231), "x"),)
            ),
            GenericType(
                (236, 243), Name((236, 240), "List"), (ASTTypeVar((241, 242), "x"),)
            ),
        ),
    ),
    {ASTTypeVar((219, 220), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((244, 245), "*")] = TypeScheme(
    FuncType(
        (247, 258),
        ASTTypeVar((247, 248), "x"),
        FuncType(
            (252, 258),
            ASTTypeVar((252, 253), "x"),
            ASTTypeVar((257, 258), "x"),
        ),
    ),
    {ASTTypeVar((247, 248), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((259, 260), "/")] = TypeScheme(
    FuncType(
        (262, 273),
        ASTTypeVar((262, 263), "x"),
        FuncType(
            (267, 273),
            ASTTypeVar((267, 268), "x"),
            ASTTypeVar((272, 273), "x"),
        ),
    ),
    {ASTTypeVar((262, 263), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((274, 275), "%")] = TypeScheme(
    FuncType(
        (277, 288),
        ASTTypeVar((277, 278), "x"),
        FuncType(
            (282, 288),
            ASTTypeVar((282, 283), "x"),
            ASTTypeVar((287, 288), "x"),
        ),
    ),
    {ASTTypeVar((277, 278), "x")},
)
DEFAULT_OPERATOR_TYPES[Name((289, 290), "^")] = TypeScheme(
    FuncType(
        (292, 303),
        ASTTypeVar((292, 293), "x"),
        FuncType(
            (297, 303),
            ASTTypeVar((297, 298), "x"),
            ASTTypeVar((302, 303), "x"),
        ),
    ),
    {ASTTypeVar((292, 293), "x")},
)

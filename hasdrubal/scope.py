from typing import Dict, Generic, Iterator, Optional, Protocol, Tuple, TypeVar

from errors import UndefinedNameError

ValType = TypeVar("ValType")


class _HasValueString(Protocol):
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

    def __contains__(self, name: _HasValueString) -> bool:
        return name.value in self._data or (
            self.parent is not None and name in self.parent
        )

    def __delitem__(self, name: _HasValueString) -> None:
        if name in self:
            del self._data[name.value]
        elif self.parent is not None:
            del self.parent[name]

    def __iter__(self) -> Iterator[Tuple[str, ValType]]:
        for key, value in self._data.items():
            yield (key, value)

    def __getitem__(self, name: _HasValueString) -> ValType:
        if name.value in self._data:
            return self._data[name.value]
        if self.parent is not None:
            return self.parent[name]
        raise UndefinedNameError(name)

    def __setitem__(self, name: _HasValueString, value: ValType) -> None:
        if name in self and self.parent is not None:
            self.parent[name] = value
        else:
            self._data[name.value] = value

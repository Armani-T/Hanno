from abc import ABC, abstractmethod
from typing import Collection, final, Iterable, Optional, Sequence, Tuple, Union

ValidScalarTypes = Union[bool, int, float, str]
Span = Tuple[int, int]


class ASTNode(ABC):
    """
    The base of all the nodes used in the AST.

    Attributes
    ----------
    span: Span
        The position in the source text that this AST node came from.
    """

    def __init__(self, span: Span) -> None:
        self.span: Span = span

    @abstractmethod
    def visit(self, visitor):
        """Run `visitor` on this node by selecting the correct node."""

    def __bool__(self) -> bool:
        return True


class Annotation(ASTNode):
    __slots__ = ("name", "span", "type_")

    def __init__(self, span: Span, name: "Name", type_: "Type") -> None:
        super(Annotation, self).__init__(span)
        self.name: Name = name
        self.type_: "Type" = type_

    def visit(self, visitor):
        return visitor.visit_annotation(self)

    def __eq__(self, other):
        if isinstance(other, Annotation):
            return self.name == other.name and self.type_ == other.type_
        return NotImplemented

    def __hash__(self):
        return hash(self.name)


class Apply(ASTNode):
    __slots__ = ("arg", "func", "span")

    def __init__(self, span: Span, func: ASTNode, arg: ASTNode) -> None:
        super().__init__(span)
        self.func: ASTNode = func
        self.arg: ASTNode = arg

    def visit(self, visitor):
        return visitor.visit_apply(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Apply):
            return self.func == other.func and self.arg == other.arg
        return NotImplemented

    __hash__ = object.__hash__


class Block(ASTNode):
    __slots__ = ("body", "span")

    def __init__(self, span: Span, body: Sequence[ASTNode]) -> None:
        if not body:
            raise ValueError("A block cannot have 0 expressions inside.")

        super().__init__(span)
        self.body: Sequence[ASTNode] = body

    @classmethod
    def new(cls, span: Span, body: Sequence[ASTNode]):
        """
        Create a block of code or `Unit` depending on the number of
        instructions.
        """
        if not body:
            return Unit(span)
        if len(body) == 1:
            return body[0]
        return cls(span, body)

    def visit(self, visitor):
        return visitor.visit_block(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Block):
            return all(
                self_elem == other_elem
                for self_elem, other_elem in zip(self.body, other.body)
            )
        if len(self.body) == 1:
            return self.body[0] == other
        return NotImplemented

    def __len__(self) -> int:
        return len(self.body)

    __hash__ = object.__hash__


class Cond(ASTNode):
    __slots__ = ("cons", "else_", "pred", "span")

    def __init__(
        self, span: Span, pred: ASTNode, cons: ASTNode, else_: ASTNode
    ) -> None:
        super().__init__(span)
        self.pred: ASTNode = pred
        self.cons: ASTNode = cons
        self.else_: ASTNode = else_

    def visit(self, visitor):
        return visitor.visit_cond(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Cond):
            return (
                self.pred == other.pred
                and self.cons == other.cons
                and self.else_ == other.else_
            )
        return NotImplemented

    __hash__ = object.__hash__


class Define(ASTNode):
    __slots__ = ("span", "target", "value")

    def __init__(self, span: Span, target: "Pattern", value: ASTNode) -> None:
        super().__init__(span)
        self.target: Pattern = target
        self.value: ASTNode = value

    def visit(self, visitor):
        return visitor.visit_define(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Define):
            return self.target == other.target and self.value == other.value
        return NotImplemented

    __hash__ = object.__hash__


class Function(ASTNode):
    __slots__ = ("body", "param", "span")

    def __init__(self, span: Span, param: "Pattern", body: ASTNode) -> None:
        super().__init__(span)
        self.param: Pattern = param
        self.body: ASTNode = body

    def visit(self, visitor):
        return visitor.visit_function(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Function):
            return self.param == other.param and self.body == other.body
        return NotImplemented

    __hash__ = object.__hash__


class Impl(ASTNode):
    __slots__ = ("methods", "name", "parent", "span")

    def __init__(
        self, span: Span, name: "Type", parent: "TypeName", methods: Collection[Define]
    ) -> None:
        super().__init__(span)
        self.name: "Type" = name
        self.parent: "TypeName" = parent
        self.methods: Collection[Define] = methods

    def visit(self, visitor):
        return visitor.visit_impl(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Impl):
            return (
                self.name == other.name
                and self.parent == other.parent
                and self.methods == other.methods
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)


class List(ASTNode):
    __slots__ = ("elements", "span")

    def __init__(self, span: Span, elements: Iterable[ASTNode]) -> None:
        super().__init__(span)
        self.elements: Iterable[ASTNode] = elements

    def visit(self, visitor):
        return visitor.visit_list(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, List):
            return all(
                map(
                    lambda elems: elems[0] == elems[1],
                    zip(self.elements, other.elements),
                )
            )
        return NotImplemented

    __hash__ = object.__hash__


class Match(ASTNode):
    __slots__ = ("cases", "span", "subject")

    def __init__(
        self, span: Span, subject: ASTNode, cases: Sequence[Tuple["Pattern", ASTNode]]
    ) -> None:
        super().__init__(span)
        self.subject: ASTNode = subject
        self.cases: Sequence[Tuple[Pattern, ASTNode]] = cases

    def visit(self, visitor):
        return visitor.visit_match(self)

    def __eq__(self, other):
        return (
            isinstance(other, Match)
            and self.subject == other.subject
            and all(
                self_case == other_case
                for self_case, other_case in zip(self.cases, other.cases)
            )
        )

    __hash__ = object.__hash__


class Name(ASTNode):
    __slots__ = ("span", "value")

    def __init__(self, span: Span, value: Optional[str]) -> None:
        if value is None:
            raise TypeError("`value` is supposed to be a string, not None.")

        super().__init__(span)
        self.value: str = value

    def visit(self, visitor):
        return visitor.visit_name(self)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        if isinstance(other, Name):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)


class Pair(ASTNode):
    __slots__ = ("first", "second", "span")

    def __init__(self, span: Span, first: ASTNode, second: ASTNode) -> None:
        super().__init__(span)
        self.first: ASTNode = first
        self.second: ASTNode = second

    def visit(self, visitor):
        return visitor.visit_pair(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Pair):
            return self.first == other.first and self.second == other.second
        return NotImplemented

    __hash__ = object.__hash__


class Pattern(ASTNode):
    @final
    def visit(self, visitor):
        return visitor.visit_pattern(self)


class FreeName(Pattern):
    def __init__(self, span: Span, value: str) -> None:
        super().__init__(span)
        self.value: str = value

    def __eq__(self, other) -> bool:
        if isinstance(other, FreeName):
            return self.value == other.value
        return NotImplemented


class ListPattern(Pattern):
    def __init__(
        self, span: Span, initial_patterns: Sequence[Pattern], rest: Optional[FreeName]
    ) -> None:
        super().__init__(span)
        self.initial_patterns: Sequence[Pattern] = initial_patterns
        self.rest: Optional[FreeName] = rest

    def __eq__(self, other) -> bool:
        if isinstance(other, ListPattern):
            return self.initial_patterns == other.initial_patterns
        return NotImplemented


class PairPattern(Pattern):
    def __init__(self, span: Span, first: Pattern, second: Pattern) -> None:
        super().__init__(span)
        self.first: Pattern = first
        self.second: Pattern = second

    def __eq__(self, other) -> bool:
        if isinstance(other, PairPattern):
            return self.first == other.first and self.second == other.second
        return NotImplemented


class PinnedName(Pattern):
    def __init__(self, span: Span, value: str) -> None:
        super().__init__(span)
        self.value: str = value

    def __eq__(self, other) -> bool:
        if isinstance(other, (PinnedName, Name)):
            return self.value == other.value
        return NotImplemented


class ScalarPattern(Pattern):
    def __init__(self, span: Span, value: ValidScalarTypes) -> None:
        super().__init__(span)
        self.value: ValidScalarTypes = value

    def __eq__(self, other) -> bool:
        if isinstance(other, ScalarPattern):
            return self.value == other.value
        return NotImplemented


class UnitPattern(Pattern):
    def __eq__(self, other) -> bool:
        return isinstance(other, UnitPattern)


class Scalar(ASTNode):
    __slots__ = ("span", "value")

    def __init__(self, span: Span, value: ValidScalarTypes) -> None:
        super().__init__(span)
        self.value: ValidScalarTypes = value

    def visit(self, visitor):
        return visitor.visit_scalar(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Scalar):
            return self.value == other.value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)


class Trait(ASTNode):
    __slots__ = ("span", "methods", "name", "parents")

    def __init__(
        self,
        span: Span,
        name: "Type",
        parents: Collection["TypeName"],
        methods: Collection[Annotation],
    ) -> None:
        super().__init__(span)
        self.methods: Collection[Annotation] = methods
        self.name: "Type" = name
        self.parents: Collection["TypeName"] = parents

    def visit(self, visitor):
        return visitor.visit_trait(self)

    def __eq__(self, other) -> bool:
        if isinstance(other, Trait):
            return (
                self.name == other.name
                and self.parents == other.parents
                and self.methods == other.methods
            )
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.name)


class Unit(ASTNode):
    __slots__ = ("span",)

    def visit(self, visitor):
        return visitor.visit_unit(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, Unit)

    def __hash__(self) -> int:
        return 0

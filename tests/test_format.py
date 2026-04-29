from pytest import mark

from context import base, pprint, types

span = (0, 0)


@mark.error_handling
def test_show_type_var_with_name():
    type_var = types.TypeVar((0, 0), "t")
    assert pprint.show_type_var(type_var) == "t"
    assert pprint.show_type_var(type_var) not in tuple(pprint.var_names.values())


@mark.error_handling
def test_show_type_var_with_int_name():
    type_var = types.TypeVar.unknown((0, 0))
    pprint.var_names[type_var.value] = "a"
    assert pprint.show_type_var(type_var) == "a"
    assert pprint.show_type_var(type_var) in tuple(pprint.var_names.values())


@mark.error_handling
def test_show_type_var_unknown():
    type_var = types.TypeVar.unknown((0, 0))
    assert len(pprint.show_type_var(type_var)) == 1
    assert pprint.show_type_var(type_var) not in pprint.available_letters
    assert pprint.show_type_var(type_var) in pprint.USABLE_LETTERS
    assert pprint.show_type_var(type_var) in tuple(pprint.var_names.values())


@mark.error_handling
@mark.parametrize(
    "node,untyped_expected,typed_expected,lowered_expected",
    (
        (base.ListPattern(span, (), None), "[]", "[]", None),
        (
            base.ListPattern(
                span,
                (base.FreeName(span, "first"), base.UnitPattern(span)),
                None,
            ),
            "[first, ()]",
            "[first, ()]",
            None,
        ),
        (
            base.ListPattern(
                span,
                (
                    base.PinnedName(span, "first"),
                    base.PairPattern(
                        span,
                        base.ScalarPattern(span, 3.142),
                        base.FreeName(span, "radius"),
                    ),
                ),
                base.FreeName(span, "rest"),
            ),
            "[^first, (3.142, radius), ..rest]",
            "[^first, (3.142, radius), ..rest]",
            None,
        ),
    ),
)
def test_typed_and_untyped_ast_printers(node, untyped_expected, typed_expected, lowered_expected):
    assert node.visit(pprint.ASTPrinter()) == untyped_expected
    assert node.visit(pprint.TypedASTPrinter()) == typed_expected
    if lowered_expected is not None:
        assert node.visit(pprint.LoweredASTPrinter()) == lowered_expected

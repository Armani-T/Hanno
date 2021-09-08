# pylint: disable=C0116, W0612
from codecs import lookup

from pytest import mark

from context import args
from utils import FakeNamespace


@mark.cmd
@mark.parametrize(
    "cmd_args,expected_",
    (
        ((), {}),
        (("-?",), {"show_help": True}),
        (
            ("--lex", "-e", "utf16"),
            {"encoding": "utf16", "show_tokens": True},
        ),
    ),
)
def test_build_config(cmd_args, expected_):
    namespace = FakeNamespace()
    args.parser.parse_args(args=cmd_args, namespace=namespace)
    config = args.build_config(namespace)
    expected = args.DEFAULT_CONFIG | expected_

    assert callable(config.report_error)
    assert callable(config.writer)
    assert lookup(config.encoding) == lookup(expected.encoding)
    assert expected.file == config.file
    assert expected.show_ast == config.show_ast
    assert expected.show_help == config.show_help
    assert expected.show_version == config.show_version
    assert expected.show_tokens == config.show_tokens
    assert expected.show_types == config.show_types
    assert expected.sort_defs == config.sort_defs

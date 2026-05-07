from codecs import lookup
from pathlib import Path
from sys import stderr, stdout

from pytest import mark, raises

from context import args, errors


class FakeNamespace:
    """
    This class is a dummy object for mocking references to attributes
    in the `argparse.namespace` class.
    """


@mark.cmd
@mark.parametrize(
    "cmd_args,expected",
    (
        ((), {}),
        (("-?",), {"show_help": True}),
        (
            ("--lex", "-e", "utf16"),
            {"encoding": "utf16", "show_tokens": True},
        ),
    ),
)
def test_build_config(cmd_args, expected):
    namespace = FakeNamespace()
    args.parser.parse_args(args=cmd_args, namespace=namespace)
    config = args.build_config(namespace)
    expected = args.DEFAULT_CONFIG | expected

    assert lookup(config.encoding) == lookup(expected.encoding)
    assert expected.file == config.file
    assert expected.show_ast == config.show_ast
    assert expected.show_help == config.show_help
    assert expected.show_version == config.show_version
    assert expected.show_tokens == config.show_tokens
    assert expected.show_types == config.show_types
    assert expected.sort_defs == config.sort_defs
    assert len(config.writers) == 2
    assert all(map(callable, config.writers))


@mark.cmd
@mark.parametrize(
    "data",
    (
        {},
        {
            "encoding": lookup("Latin-1"),
            "show_types": True,
            "sort_defs": False,
            "show_version": True,
        },
        args.DEFAULT_CONFIG,
        args.ConfigData(
            file=None,
            encoding=lookup("ASCII"),
            compress=True,
            expansion_level=10,
            out_file="stderr",
            show_ast=True,
            show_help=True,
            show_version=False,
            show_tokens=True,
            show_types=False,
            sort_defs=True,
            writers=(),
        ),
    ),
)
def test_config_data_or(data):
    config = args.DEFAULT_CONFIG | data
    keys = (
        "file",
        "encoding",
        "compress",
        "expansion_level",
        "out_file",
        "show_ast",
        "show_help",
        "show_version",
        "show_tokens",
        "show_types",
        "sort_defs",
        "writers",
    )
    for key in keys:
        if key in data:
            assert config[key] == data[key]
        else:
            assert config[key] == args.DEFAULT_CONFIG[key]


@mark.cmd
def test_config_data_or_raises():
    with raises(TypeError):
        args.DEFAULT_CONFIG | []


@mark.cmd
def test_config_data_contains_when_false():
    assert "zzzzz" not in args.DEFAULT_CONFIG


@mark.cmd
def test_get_writer():
    assert stdout.write == args.get_writer(None)
    assert stdout.write == args.get_writer("stdout")
    assert stderr.write == args.get_writer("stderr")


@mark.cmd
def test_get_writer_raises_1(monkeypatch):
    monkeypatch.setattr(Path, "touch", lambda _: None)
    with raises(errors.CMDError):
        path = Path(__file__).parent / "does-not-exist.txt"
        result = args.get_writer(str(path))


@mark.cmd
def test_get_writer_raises_2(monkeypatch):
    def throw_error(_):
        raise PermissionError

    monkeypatch.setattr(Path, "touch", throw_error)
    with raises(errors.CMDError):
        path = Path(__file__).parent / "does-not-exist.txt"
        result = args.get_writer(str(path))

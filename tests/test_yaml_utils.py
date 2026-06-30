"""Tests for autotag_metadata.core.yaml_utils."""
from autotag_metadata.core.yaml_utils import (
    dump_yaml,
    dump_yaml_to_file,
    parse_yaml,
    validate_yaml_syntax,
    yaml_ancestor_path,
)


DOC = (
    "electrochemical system:\n"
    "  electrolyte:\n"
    "    type: aq\n"
    "    components:\n"
    "    - name: water\n"
    "      sum formula: H2O\n"
    "    - name: sulfuric acid\n"
    "      type: acid\n"
)


def test_ancestor_path_mapping_selection():
    assert yaml_ancestor_path(DOC, 2, 2) == "electrochemical system.electrolyte"


def test_ancestor_path_same_indent_sequence_full_list():
    # Selecting the whole component list anchors under "components", not the
    # parent mapping — the items are level-indented with the key.
    assert yaml_ancestor_path(DOC, 4, 7) == "electrochemical system.electrolyte.components"


def test_ancestor_path_same_indent_sequence_single_item_with_sibling_above():
    # Selecting only the second item must still find "components" past the
    # preceding sibling item.
    assert yaml_ancestor_path(DOC, 6, 7) == "electrochemical system.electrolyte.components"


def test_ancestor_path_indented_sequence_style():
    doc = "e:\n  c:\n    - name: water\n    - name: acid\n"
    assert yaml_ancestor_path(doc, 2, 3) == "e.c"


def test_validate_yaml_syntax_valid():
    assert validate_yaml_syntax("key: value\nnested:\n  a: 1") is None


def test_validate_yaml_syntax_invalid():
    error = validate_yaml_syntax("key: :")
    assert error is not None


def test_validate_yaml_syntax_empty():
    assert validate_yaml_syntax("") is None


def test_parse_yaml_dict():
    result = parse_yaml("a: 1\nb: hello")
    assert result == {"a": 1, "b": "hello"}


def test_parse_yaml_none_on_empty():
    assert parse_yaml("") is None


def test_parse_yaml_nested():
    result = parse_yaml("outer:\n  inner: 42")
    assert result == {"outer": {"inner": 42}}


def test_dump_yaml_produces_string():
    result = dump_yaml({"a": 1, "b": "hello"})
    assert isinstance(result, str)
    assert "a: 1" in result
    assert "b: hello" in result


def test_dump_yaml_preserves_key_order():
    data = {"z_key": 1, "a_key": 2}
    result = dump_yaml(data)
    assert result.index("z_key") < result.index("a_key")


def test_round_trip():
    original = {"experiment": "cv", "voltage": 1.5, "cycles": 3}
    assert parse_yaml(dump_yaml(original)) == original


def test_dump_yaml_to_file(tmp_path):
    f = tmp_path / "output.yaml"
    data = {"key": "value", "number": 99}
    dump_yaml_to_file(data, str(f))
    assert f.exists()
    assert parse_yaml(f.read_text(encoding="utf-8")) == data

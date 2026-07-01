"""Tests for TemplateTree dict↔model conversion and round-trip."""
import pytest


@pytest.fixture(scope="module")
def tree_factory(qapp):
    """Return a factory that creates TemplateTree instances (requires qapp)."""
    from autotag_metadata.ui.template_tree import TemplateTree

    def make(data):
        return TemplateTree(data)

    return make


def test_dict_to_model_flat(tree_factory):
    items = tree_factory({"a": "hello", "b": 42}).dict_to_model({"a": "hello", "b": 42})
    assert len(items) == 2
    keys = [i["key"] for i in items]
    assert "a" in keys
    assert "b" in keys


def test_dict_to_model_types(tree_factory):
    items = tree_factory({}).dict_to_model({"s": "text", "i": 1, "f": 3.14})
    by_key = {i["key"]: i for i in items}
    assert by_key["s"]["type"] == str(type(""))
    assert by_key["i"]["type"] == str(type(0))
    assert by_key["f"]["type"] == str(type(0.0))


def test_dict_to_model_nested(tree_factory):
    data = {"section": {"x": 1, "y": 2}}
    items = tree_factory(data).dict_to_model(data)
    # "section" parent + 2 children
    assert len(items) == 3
    assert items[0]["key"] == "section"
    assert items[0]["val"] == ""  # nested dict has empty val


def test_dict_to_model_with_list(tree_factory):
    data = {"items": [10, 20, 30]}
    items = tree_factory(data).dict_to_model(data)
    # "items" parent + 3 children
    assert len(items) == 4


def test_round_trip_simple(tree_factory):
    data = {"experiment": "cv", "cycles": 3, "operator": "alice"}
    result = tree_factory(data).to_dict()
    assert result == data


def test_round_trip_floats(tree_factory):
    data = {"voltage": 1.5, "current": 0.01}
    result = tree_factory(data).to_dict()
    assert result == data


def test_round_trip_nested(tree_factory):
    data = {"section": {"voltage": 1.5, "label": "test"}}
    result = tree_factory(data).to_dict()
    assert result == data

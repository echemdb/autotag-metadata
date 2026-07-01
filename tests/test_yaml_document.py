"""Tests for autotag_metadata.core.yaml_document."""
import pytest

from autotag_metadata.core.yaml_document import YamlDocument


def test_init_empty():
    doc = YamlDocument()
    assert doc.data == {}


def test_init_with_data():
    data = {"a": 1, "b": {"c": 2}}
    doc = YamlDocument(data)
    assert doc.data is data


def test_init_none_becomes_empty():
    doc = YamlDocument(None)
    assert doc.data == {}


def test_data_setter():
    doc = YamlDocument({"old": 1})
    doc.data = {"new": 2}
    assert doc.data == {"new": 2}


def test_data_setter_none_becomes_empty():
    doc = YamlDocument({"a": 1})
    doc.data = None
    assert doc.data == {}


# -- get_subtree -----------------------------------------------------------


def test_get_subtree_empty_path_returns_full_doc():
    data = {"x": 1, "y": {"z": 2}}
    doc = YamlDocument(data)
    assert doc.get_subtree("") is data


def test_get_subtree_top_level_key():
    doc = YamlDocument({"a": {"b": 1}, "c": 2})
    assert doc.get_subtree("a") == {"b": 1}


def test_get_subtree_nested():
    doc = YamlDocument({"a": {"b": {"c": 42}}})
    assert doc.get_subtree("a.b") == {"c": 42}


def test_get_subtree_missing_key_returns_empty():
    doc = YamlDocument({"a": 1})
    assert doc.get_subtree("missing") == {}


def test_get_subtree_missing_nested_key_returns_empty():
    doc = YamlDocument({"a": {"b": 1}})
    assert doc.get_subtree("a.missing") == {}


def test_get_subtree_non_dict_value_returns_empty():
    doc = YamlDocument({"a": 42})
    assert doc.get_subtree("a") == {}


def test_get_subtree_path_through_non_dict_returns_empty():
    doc = YamlDocument({"a": 42})
    assert doc.get_subtree("a.b") == {}


def test_get_subtree_list_index():
    doc = YamlDocument({"e": {"components": [{"name": "water"}, {"name": "acid"}]}})
    assert doc.get_subtree("e.components.0") == {"name": "water"}
    assert doc.get_subtree("e.components.1") == {"name": "acid"}
    assert doc.get_subtree("e.components.-1") == {"name": "acid"}


def test_get_subtree_list_index_out_of_range_returns_empty():
    doc = YamlDocument({"e": {"components": [{"name": "water"}]}})
    assert doc.get_subtree("e.components.5") == {}
    assert doc.get_subtree("e.components.notanint") == {}


def test_set_subtree_list_index_writes_element():
    doc = YamlDocument({"e": {"components": [{"name": "water"}, {"name": "acid"}]}})
    doc.set_subtree("e.components.0", {"name": "water", "type": "solvent"})
    assert doc.data["e"]["components"][0] == {"name": "water", "type": "solvent"}
    assert doc.data["e"]["components"][1] == {"name": "acid"}


def test_set_subtree_list_index_out_of_range_is_noop():
    doc = YamlDocument({"e": {"components": [{"name": "water"}]}})
    doc.set_subtree("e.components.3", {"name": "x"})
    assert doc.data["e"]["components"] == [{"name": "water"}]


def test_resolve_scalar_leaf():
    doc = YamlDocument({"e": {"components": [{"type": "solvent"}]}})
    assert doc.resolve("e.components.0.type") == (True, "solvent")
    assert doc.resolve("e.components.0.missing") == (False, None)
    assert doc.resolve("") == (True, doc.data)


def test_set_subtree_writes_scalar_leaf():
    doc = YamlDocument({"e": {"components": [{"name": "water", "type": "solvent"}]}})
    doc.set_subtree("e.components.0.type", "acid")
    assert doc.data["e"]["components"][0] == {"name": "water", "type": "acid"}


def test_get_subtree_list_value_returned_intact():
    # A list-valued subtree (e.g. electrolyte.components) must survive being
    # read so it can be captured as a snippet without being dropped.
    doc = YamlDocument({"electrolyte": {"components": [{"name": "water"}]}})
    assert doc.get_subtree("electrolyte.components") == [{"name": "water"}]


def test_list_subtree_capture_then_merge_adds_items():
    # Regression: capturing a panel zoomed on a list path used to yield an empty
    # dict, so applying it later (non-destructively) added nothing.
    from autotag_metadata.core.yaml_document import nest_at_path, non_destructive_merge

    doc = YamlDocument({"electrolyte": {"components": [{"name": "water"}]}})
    captured = nest_at_path("electrolyte.components", doc.get_subtree("electrolyte.components"))
    assert captured == {"electrolyte": {"components": [{"name": "water"}]}}

    snippet = {"electrolyte": {"components": [{"name": "water"}, {"name": "KOH"}]}}
    merged = non_destructive_merge({"electrolyte": {"components": [{"name": "water"}]}}, snippet)
    assert merged["electrolyte"]["components"] == [{"name": "water"}, {"name": "KOH"}]


def test_indexed_element_capture_then_merge_enriches_by_name():
    # Capturing a single list element by index (components.0) must anchor it as a
    # one-item list (not a "0" dict key), so re-applying enriches the match.
    from autotag_metadata.core.yaml_document import nest_at_path, non_destructive_merge

    doc = YamlDocument({"electrolyte": {"components": [{"name": "water", "type": "solvent"}]}})
    path = "electrolyte.components.0"
    captured = nest_at_path(path, doc.get_subtree(path))
    assert captured == {"electrolyte": {"components": [{"name": "water", "type": "solvent"}]}}

    target = {"electrolyte": {"components": [{"name": "water"}]}}
    merged = non_destructive_merge(target, captured)
    assert merged["electrolyte"]["components"] == [{"name": "water", "type": "solvent"}]


# -- set_subtree -----------------------------------------------------------


def test_set_subtree_empty_path_replaces_document():
    doc = YamlDocument({"old": 1})
    doc.set_subtree("", {"new": 2})
    assert doc.data == {"new": 2}


def test_set_subtree_top_level():
    doc = YamlDocument({"a": {"b": 1}, "c": 2})
    doc.set_subtree("a", {"b": 99})
    assert doc.data == {"a": {"b": 99}, "c": 2}


def test_set_subtree_nested():
    doc = YamlDocument({"a": {"b": {"c": 1}}})
    doc.set_subtree("a.b", {"c": 99, "d": 0})
    assert doc.data == {"a": {"b": {"c": 99, "d": 0}}}


def test_set_subtree_creates_intermediate_dicts():
    doc = YamlDocument({})
    doc.set_subtree("x.y.z", {"val": 5})
    assert doc.data == {"x": {"y": {"z": {"val": 5}}}}


def test_set_subtree_overwrites_non_dict_intermediate():
    doc = YamlDocument({"a": 42})
    doc.set_subtree("a.b", {"c": 1})
    assert doc.data == {"a": {"b": {"c": 1}}}


# -- round-trip ------------------------------------------------------------


def test_get_set_round_trip():
    original = {"instrument": {"name": "potentiostat", "settings": {"rate": 10}}}
    doc = YamlDocument(original)
    subtree = doc.get_subtree("instrument.settings")
    subtree["rate"] = 20
    doc.set_subtree("instrument.settings", subtree)
    assert doc.get_subtree("instrument.settings") == {"rate": 20}
    assert doc.data["instrument"]["name"] == "potentiostat"


# -- non_destructive_merge: null placeholders ------------------------------


def test_merge_fills_existing_none_value():
    # Regression: a key present but holding YAML null (e.g. an empty
    # "electrolyte:" line) used to be treated as a type clash, so the snippet
    # was dropped. It must be filled instead.
    from autotag_metadata.core.yaml_document import non_destructive_merge

    base = {"electrochemical system": {"electrolyte": None}}
    patch = {"electrochemical system": {"electrolyte": {"type": "aq", "components": [{"name": "water"}]}}}
    merged = non_destructive_merge(base, patch)
    assert merged["electrochemical system"]["electrolyte"] == {
        "type": "aq",
        "components": [{"name": "water"}],
    }


def test_merge_fills_nested_none_value():
    from autotag_metadata.core.yaml_document import non_destructive_merge

    base = {"electrolyte": {"type": "aq", "components": None}}
    patch = {"electrolyte": {"components": [{"name": "water"}]}}
    merged = non_destructive_merge(base, patch)
    assert merged["electrolyte"] == {"type": "aq", "components": [{"name": "water"}]}


def test_merge_does_not_overwrite_real_scalar_with_none():
    from autotag_metadata.core.yaml_document import non_destructive_merge

    base = {"a": 5}
    patch = {"a": None}
    assert non_destructive_merge(base, patch) == {"a": 5}


# -- non_destructive_merge: list items merged by name ----------------------


def test_merge_enriches_existing_component_by_name():
    # Regression: a partially-filled component must be enriched in place from
    # the snippet (matched by name) rather than appended as a duplicate, and a
    # genuinely new component is appended.
    from autotag_metadata.core.yaml_document import non_destructive_merge

    base = {"electrolyte": {"components": [{"name": "water", "sum formula": "H2O"}]}}
    patch = {
        "electrolyte": {
            "components": [
                {"name": "water", "sum formula": "H2O", "type": "solvent"},
                {"name": "sulfuric acid", "type": "acid"},
            ]
        }
    }
    components = non_destructive_merge(base, patch)["electrolyte"]["components"]
    assert components == [
        {"name": "water", "sum formula": "H2O", "type": "solvent"},
        {"name": "sulfuric acid", "type": "acid"},
    ]


def test_merge_keeps_existing_component_field_over_snippet():
    # Non-destructive: an existing value on a matched component wins.
    from autotag_metadata.core.yaml_document import non_destructive_merge

    base = {"c": [{"name": "water", "type": "solvent"}]}
    patch = {"c": [{"name": "water", "type": "OTHER", "ph": 7}]}
    assert non_destructive_merge(base, patch)["c"] == [{"name": "water", "type": "solvent", "ph": 7}]

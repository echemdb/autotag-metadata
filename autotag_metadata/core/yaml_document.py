"""Path-based accessor for nested YAML/dict structures."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2026 Johannes Hermann
#
#  autotag-metadata is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  autotag-metadata is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with autotag-metadata. If not, see
#  <https://www.gnu.org/licenses/>.
# ********************************************************************

import copy


def non_destructive_merge(base: dict, patch: dict) -> dict:
    """Merge *patch* into *base* without ever overwriting existing data.

    Used to apply a snippet additively:

    * new keys are added;
    * a key present but holding ``None`` (a YAML ``null`` placeholder, e.g. an
      empty ``electrolyte:`` line) is treated as absent and filled from the
      patch — filling a blank does not overwrite real data;
    * two mappings merge recursively;
    * two lists are extended with the patch items not already present (by
      value);
    * an existing scalar, or any type clash, is left untouched (the patch's
      value at that key is dropped).

    Returns a new structure; neither argument is mutated.

    >>> non_destructive_merge({"a": {"x": 1}}, {"a": {"y": 2}, "b": 3})
    {'a': {'x': 1, 'y': 2}, 'b': 3}
    >>> non_destructive_merge({"e": [{"name": "WE"}]}, {"e": [{"name": "WE"}, {"name": "CE"}]})
    {'e': [{'name': 'WE'}, {'name': 'CE'}]}
    >>> non_destructive_merge({"t": ["a"]}, {"t": ["a", "b"]})
    {'t': ['a', 'b']}
    >>> non_destructive_merge({"g": 5}, {"g": 3})
    {'g': 5}
    >>> non_destructive_merge({"electrolyte": None}, {"electrolyte": {"type": "aq"}})
    {'electrolyte': {'type': 'aq'}}
    """
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if key not in result or result[key] is None:
            result[key] = copy.deepcopy(value)
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = non_destructive_merge(result[key], value)
        elif isinstance(result[key], list) and isinstance(value, list):
            result[key] = _merge_lists(result[key], value)
        # else: existing scalar or type clash -> keep existing, drop patch value
    return result


def overwrite_merge(base: dict, patch: dict) -> dict:
    """Merge *patch* into *base*; the patch wins on conflict.

    Mappings merge recursively; for everything else (scalars, lists, type
    clashes) the patch value replaces the base value. New keys are added.
    Returns a new structure; neither argument is mutated.

    >>> overwrite_merge({"a": {"x": 1}, "g": 5}, {"a": {"y": 2}, "g": 3})
    {'a': {'x': 1, 'y': 2}, 'g': 3}
    >>> overwrite_merge({"t": ["a"]}, {"t": ["b"]})
    {'t': ['b']}
    """
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = overwrite_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _merge_lists(existing: list, incoming: list) -> list:
    """Merge *incoming* into *existing*.

    Dict items carrying a ``name`` are matched by that name: a matching item is
    merged in place (non-destructively, so existing values win but blanks fill),
    while an unseen name is appended. This is how component-style lists work
    (``electrolyte.components``): re-applying a snippet enriches the existing
    ``water`` entry rather than appending a second one. Non-dict items (or dicts
    without a ``name``) are appended only when not already present by value.

    >>> _merge_lists([{"name": "water", "ph": 7}], [{"name": "water", "type": "solvent"}])
    [{'name': 'water', 'ph': 7, 'type': 'solvent'}]
    >>> _merge_lists([{"name": "water"}], [{"name": "acid"}])
    [{'name': 'water'}, {'name': 'acid'}]
    >>> _merge_lists(["a"], ["a", "b"])
    ['a', 'b']
    """
    merged = copy.deepcopy(existing)
    for item in incoming:
        name = _item_name(item)
        if name is not None:
            match = next((i for i, m in enumerate(merged) if _item_name(m) == name), None)
            if match is not None:
                merged[match] = non_destructive_merge(merged[match], item)
                continue
            merged.append(copy.deepcopy(item))
        elif item not in merged:
            merged.append(copy.deepcopy(item))
    return merged


def _item_name(item) -> object | None:
    """Identity of a list item for merge matching: its ``name``, else ``None``."""
    if isinstance(item, dict):
        return item.get("name")
    return None


def _as_index(key: str, length: int) -> int | None:
    """Parse *key* as a list index valid for a list of *length*, else ``None``.

    Supports negative indices; returns ``None`` for non-numeric or out-of-range
    keys so callers can treat the path as missing.

    >>> _as_index("0", 2)
    0
    >>> _as_index("-1", 2)
    -1
    >>> _as_index("5", 2) is None
    True
    >>> _as_index("name", 2) is None
    True
    """
    try:
        index = int(key)
    except ValueError:
        return None
    return index if -length <= index < length else None


def _is_index_segment(key: str) -> bool:
    """Whether a path segment denotes a list index (a plain integer)."""
    try:
        int(key)
        return True
    except ValueError:
        return False


def nest_at_path(path: str, data: dict) -> dict | list:
    """Wrap *data* under the keys of *path* (dotted), anchoring it from the root.

    Empty *path* returns *data* unchanged. Used to save a panel's subtree
    together with its parent structure, so the snippet re-inserts at the right
    point in the document. A numeric segment denotes a list element: the data is
    wrapped in a single-item list under its parent key, so a snippet captured
    from ``components.0`` re-applies through the list merge (matched by ``name``)
    rather than landing under a literal ``"0"`` key.

    >>> nest_at_path("instrument.settings", {"gain": 3})
    {'instrument': {'settings': {'gain': 3}}}
    >>> nest_at_path("electrolyte.components.0", {"name": "water"})
    {'electrolyte': {'components': [{'name': 'water'}]}}
    >>> nest_at_path("", {"gain": 3})
    {'gain': 3}
    """
    result: dict | list = data
    for key in reversed(path.split(".")) if path else []:
        if _is_index_segment(key):
            result = [result]
        else:
            result = {key: result}
    return result


class YamlDocument:
    """Holds a YAML document as a dict with dotted-path accessors.

    >>> doc = YamlDocument({"a": {"b": {"c": 1}}})
    >>> doc.get_subtree("a.b")
    {'c': 1}
    >>> doc.set_subtree("a.b", {"c": 99})
    >>> doc.data
    {'a': {'b': {'c': 99}}}
    """

    def __init__(self, data: dict | None = None):
        self._data: dict = data if data is not None else {}

    @property
    def data(self) -> dict:
        return self._data

    @data.setter
    def data(self, value: dict) -> None:
        self._data = value if value is not None else {}

    def get_subtree(self, path: str) -> dict | list:
        """Return the subtree at *path* (dotted, e.g. ``"a.b.c"``).

        Returns the node when it is a dict or a list; returns an empty dict
        when the path does not exist or resolves to a scalar. Empty *path*
        returns the full document. Lists are returned intact so that
        list-valued subtrees (e.g. ``electrolyte.components``) survive being
        captured as snippets. A numeric segment indexes into a list, so a
        single list element can be zoomed onto, e.g. ``components.0``.

        >>> doc = YamlDocument({"x": {"y": 1}, "z": 2, "c": [{"name": "WE"}]})
        >>> doc.get_subtree("")
        {'x': {'y': 1}, 'z': 2, 'c': [{'name': 'WE'}]}
        >>> doc.get_subtree("x")
        {'y': 1}
        >>> doc.get_subtree("c")
        [{'name': 'WE'}]
        >>> doc.get_subtree("c.0")
        {'name': 'WE'}
        >>> doc.get_subtree("c.5")
        {}
        >>> doc.get_subtree("x.missing")
        {}
        >>> doc.get_subtree("z")
        {}
        """
        found, node = self.resolve(path)
        if not found:
            return {}
        return node if isinstance(node, (dict, list)) else {}

    def resolve(self, path: str) -> tuple[bool, object]:
        """Resolve *path* to its raw node of any type.

        Returns ``(found, value)``. Unlike :meth:`get_subtree`, scalars are
        returned as-is (not flattened to ``{}``), so a leaf value such as
        ``components.0.type`` can be zoomed onto and edited. ``found`` is False
        when any segment is missing or indexes a non-container.

        >>> doc = YamlDocument({"c": [{"type": "solvent"}]})
        >>> doc.resolve("c.0.type")
        (True, 'solvent')
        >>> doc.resolve("c.0.missing")
        (False, None)
        """
        if not path:
            return True, self._data
        node = self._data
        for key in path.split("."):
            if isinstance(node, dict):
                if key not in node:
                    return False, None
                node = node[key]
            elif isinstance(node, list):
                index = _as_index(key, len(node))
                if index is None:
                    return False, None
                node = node[index]
            else:
                return False, None
        return True, node

    def set_subtree(self, path: str, data: object) -> None:
        """Write *data* into the document at *path*.

        *data* is usually a dict or list, but a scalar is allowed so a single
        leaf value (e.g. ``components.0.type``) can be written back. Creates
        intermediate dicts as needed. A numeric segment indexes into an existing
        list (list slots are not created, so an out-of-range index is a no-op).
        Empty *path* replaces the entire document.

        >>> doc = YamlDocument({"a": {"b": 1}})
        >>> doc.set_subtree("a", {"b": 2, "c": 3})
        >>> doc.data
        {'a': {'b': 2, 'c': 3}}
        >>> doc.set_subtree("", {"fresh": True})
        >>> doc.data
        {'fresh': True}
        >>> doc.set_subtree("x.y", {"val": 5})
        >>> doc.data
        {'fresh': True, 'x': {'y': {'val': 5}}}
        >>> doc.set_subtree("c", [{"name": "WE"}])
        >>> doc.set_subtree("c.0", {"name": "CE"})
        >>> doc.data["c"]
        [{'name': 'CE'}]
        """
        if not path:
            # The document root is always a mapping; a bare list root is not a
            # valid document, so coerce defensively.
            self._data = data if isinstance(data, dict) else {}
            return
        keys = path.split(".")
        node = self._data
        for key in keys[:-1]:
            if isinstance(node, list):
                index = _as_index(key, len(node))
                if index is None:
                    return  # cannot descend a missing/invalid list slot
                node = node[index]
            else:
                if not isinstance(node, dict):
                    return
                # Preserve an existing dict or list to descend into it; replace
                # a scalar (or missing key) with a fresh mapping.
                if key not in node or not isinstance(node[key], (dict, list)):
                    node[key] = {}
                node = node[key]
        last = keys[-1]
        if isinstance(node, list):
            index = _as_index(last, len(node))
            if index is not None:
                node[index] = data
        elif isinstance(node, dict):
            node[last] = data

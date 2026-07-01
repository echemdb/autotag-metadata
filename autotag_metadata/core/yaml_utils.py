"""YAML validation and serialization utilities."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2021-2026 Johannes Hermann
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

import yaml
from yamllint import linter


def validate_yaml_syntax(text):
    """Check whether *text* is syntactically valid YAML.

    Returns ``None`` if valid, or a ``yamllint.linter.LintProblem``
    describing the first syntax error.
    """
    return linter.get_syntax_error(text)


def parse_yaml(text):
    """Safely parse a YAML string and return the resulting object."""
    return yaml.safe_load(text)


def dump_yaml(data):
    """Serialize *data* to a YAML string."""
    return yaml.dump(data, sort_keys=False, allow_unicode=True)


def dump_yaml_to_file(data, filepath):
    """Write *data* as YAML to *filepath*."""
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _mapping_key(line: str) -> str | None:
    """Return the mapping key of *line* (text before its first colon), or None."""
    stripped = line.strip()
    if stripped.startswith("- ") or ":" not in stripped:
        return None
    return stripped.split(":", 1)[0].strip()


def yaml_ancestor_path(text: str, start_line: int, end_line: int) -> str:
    """Dotted path of the mapping keys enclosing the lines [start_line, end_line].

    Used to anchor a raw-YAML text selection at its true location: walks upward
    from the selection collecting parent keys at successively smaller
    indentation. Returns "" for a root-level selection. Stops at a sequence
    (``-``) ancestor, which cannot be expressed as a dotted path.

    A block sequence is often indented *level* with its parent key::

        components:
        - name: water

    Here the ``- `` items share ``components``'s indentation, so the plain
    smaller-indent walk would miss it. This case is detected explicitly so that
    selecting the items still anchors them under ``components``.

    >>> doc = "instrument:\\n  settings:\\n    gain: 3\\n    mode: cv\\n"
    >>> yaml_ancestor_path(doc, 2, 3)
    'instrument.settings'
    >>> yaml_ancestor_path(doc, 1, 1)
    'instrument'
    >>> yaml_ancestor_path("a: 1\\nb: 2\\n", 0, 1)
    ''
    >>> seq = "e:\\n  c:\\n  - name: water\\n  - name: acid\\n"
    >>> yaml_ancestor_path(seq, 2, 3)
    'e.c'
    """
    lines = text.split("\n")
    selected = [
        line for line in lines[start_line : end_line + 1] if line.strip() and not line.lstrip().startswith("#")
    ]
    if not selected:
        return ""
    needed = min(_indent_of(line) for line in selected)

    keys: list[str] = []
    # A block sequence whose "- " items are indented level with their parent key
    # has no smaller-indent ancestor for that key, so the walk below would skip
    # it. Find that same-indent parent key first (stepping over sibling items),
    # then let the walk continue from the key line for the remaining ancestors.
    if selected[0].lstrip().startswith("- "):
        for i in range(start_line - 1, -1, -1):
            line = lines[i]
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = _indent_of(line)
            if indent > needed:
                continue  # inside an earlier sibling item's subtree
            if indent == needed and line.lstrip().startswith("- "):
                continue  # a sibling sequence item; keep looking up
            if indent == needed:
                key = _mapping_key(line)
                value = line.split(":", 1)[1].strip() if key is not None else "x"
                if key is not None and (not value or value.startswith("#")):
                    keys.append(key)
                    start_line = i  # resume the ancestor walk above this key
            break  # a line at indent <= needed that is not a sibling item

    for i in range(start_line - 1, -1, -1):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent_of(line)
        if indent < needed:
            key = _mapping_key(line)
            if key is None:
                break
            keys.append(key)
            needed = indent
            if indent == 0:
                break
    keys.reverse()
    return ".".join(keys)


def yaml_path_at_line(text: str, line_no: int) -> str | None:
    """Relative dotted path of the YAML node starting on *line_no* (0-based).

    Composes *text* and walks the node tree, matching mapping keys and sequence
    items by their source line. Returns a dotted path (numeric segments address
    list indices, e.g. ``components.0.ph``) or ``None`` when no key or element
    starts on that line, or the text is not valid YAML. This mirrors the form
    view's structural path derivation, so the raw-YAML and form editors drill
    into the same subtree from the same line.

    >>> doc = "instrument:\\n  settings:\\n    gain: 3\\n    mode: cv\\n"
    >>> yaml_path_at_line(doc, 0)
    'instrument'
    >>> yaml_path_at_line(doc, 1)
    'instrument.settings'
    >>> yaml_path_at_line(doc, 2)
    'instrument.settings.gain'
    >>> seq = "components:\\n- name: water\\n  ph: 7\\n"
    >>> yaml_path_at_line(seq, 1)
    'components.0'
    >>> yaml_path_at_line(seq, 2)
    'components.0.ph'
    >>> yaml_path_at_line("a: 1\\n", 9) is None
    True
    """
    try:
        root = yaml.compose(text)
    except yaml.YAMLError:
        return None
    if root is None:
        return None
    return _node_path_at_line(root, line_no, "")


def _node_path_at_line(node, line_no: int, prefix: str) -> str | None:
    """Depth-first search for the mapping key or sequence item on *line_no*."""
    if isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            child = f"{prefix}.{key_node.value}" if prefix else str(key_node.value)
            if key_node.start_mark.line == line_no:
                return child
            found = _node_path_at_line(value_node, line_no, child)
            if found is not None:
                return found
    elif isinstance(node, yaml.SequenceNode):
        for i, item_node in enumerate(node.value):
            child = f"{prefix}.{i}" if prefix else str(i)
            if item_node.start_mark.line == line_no:
                return child
            found = _node_path_at_line(item_node, line_no, child)
            if found is not None:
                return found
    return None

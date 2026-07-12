"""Tests for markdown-valued metadata fields (detection, normalization, storage)."""
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

import pytest

from autotag_metadata.core.markdown_text import is_markdown_value, normalize_markdown
from autotag_metadata.core.metadata_writer import write_metadata
from autotag_metadata.core.yaml_utils import dump_yaml, parse_yaml

PROSE = "## Sample prep\n\nRinsed in **DI water**, then:\n\n- sonicated\n- dried"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("one line", False),
        ("two\nlines", True),
        ("trailing\n", True),
        ("", False),
        (7, False),
        (None, False),
        (["a\nb"], False),
    ],
)
def test_is_markdown_value(value, expected):
    assert is_markdown_value(value) is expected


def test_normalize_strips_trailing_space_and_blank_lines():
    assert normalize_markdown("a  \r\nb\t \n\n\n") == "a\nb"


def test_normalize_is_idempotent():
    once = normalize_markdown(PROSE + "\n\n")
    assert normalize_markdown(once) == once


@pytest.mark.parametrize(
    "text,expected",
    [
        # Qt escapes every literal "[" — dropped again where it cannot open a link.
        (r"Potential E \[V] vs. RHE", "Potential E [V] vs. RHE"),
        (r"Fields: \[V], \[A cm-2]", "Fields: [V], [A cm-2]"),
        # ...but a real link (or reference) keeps its escape: unescaping would create one.
        (r"a \[label](url)", r"a \[label](url)"),
        (r"a \[label][ref]", r"a \[label][ref]"),
        # a literal backslash still needs its escape
        (r"path C:\\lab", r"path C:\\lab"),
    ],
)
def test_normalize_drops_only_inert_bracket_escapes(text, expected):
    assert normalize_markdown(text) == expected


def test_normalize_keeps_single_line_single_line():
    """Editing a one-line string must not turn it into prose by adding a newline."""
    assert is_markdown_value(normalize_markdown("CV-01")) is False


def test_prose_dumps_as_block_literal():
    text = dump_yaml({"notes": PROSE})
    assert "notes: |-" in text
    assert "\\n" not in text  # never a quoted one-line scalar
    assert "  ## Sample prep" in text


def test_prose_survives_yaml_round_trip():
    doc = {"experiment": {"notes": PROSE, "name": "CV-01"}}
    assert parse_yaml(dump_yaml(doc)) == doc


def test_sidecar_keeps_prose_readable(tmp_path):
    """The written .metadata.yaml must show the prose as a block, not \\n escapes."""
    measurement = tmp_path / "data.csv"
    measurement.write_text("t,I\n0,1\n")

    write_metadata(str(measurement), {"notes": PROSE})

    written = (tmp_path / "data.csv.metadata.yaml").read_text()
    assert "notes: |-" in written
    assert parse_yaml(written)["notes"] == PROSE

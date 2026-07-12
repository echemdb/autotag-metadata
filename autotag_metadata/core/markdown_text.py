"""Markdown-valued metadata fields: detection and normalization (no Qt)."""
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

import re
from typing import Any

#: An escaped ``[`` whose ``]`` is not followed by ``(`` or ``[`` — i.e. a bracket that
#: cannot start a link or a reference, so the backslash before it is inert.
_INERT_BRACKET_ESCAPE = re.compile(r"\\\[([^\]\n]*)\](?![(\[])")


def is_markdown_value(value: Any) -> bool:
    """Whether *value* is prose that should be edited as markdown.

    The value itself decides: a string carrying a line break is prose, anything
    else is a one-line scalar. Nothing about the choice is stored outside the
    document, so a template, a snippet, a raw-YAML edit and a loaded sidecar all
    render the same way without any per-field state to keep in sync.

    >>> is_markdown_value("## Prep\\nRinsed in DI water.")
    True
    >>> is_markdown_value("CV-01")
    False
    >>> is_markdown_value(7)
    False
    """
    return isinstance(value, str) and "\n" in value


def normalize_markdown(text: str) -> str:
    """Clean up markdown *text* for storage as a YAML block literal.

    Three things happen, each forced by how the value has to survive on disk:

    * CRLF/CR line endings become ``\\n``.
    * Trailing spaces are stripped from every line — PyYAML cannot express a line
      with trailing whitespace in literal style and silently falls back to a
      quoted one-line scalar full of ``\\n`` escapes. The cost is markdown's
      two-space hard line break; Qt's markdown writer does not emit those either.
    * Trailing blank lines are dropped. Qt's writer ends its output with a blank
      line, which ``|`` (clip chomping) cannot round-trip, and which would
      otherwise accumulate on every edit.

    No trailing newline is *added*, so editing a one-line string leaves it a
    one-line string — it must not silently become prose just by being touched.

    Qt's markdown writer also escapes every literal ``[``, which this domain's prose is
    full of (``E [V]``, ``[A cm-2]``) — so an edited field would litter the sidecar with
    ``\\[V]``. The escape is dropped again where it is provably inert: a bracket that is
    not followed by ``(`` or ``[`` cannot open a link or a reference, so ``\\[V]`` and
    ``[V]`` render identically. A real link keeps its escape.

    >>> normalize_markdown("a  \\r\\nb \\n\\n")
    'a\\nb'
    >>> normalize_markdown("only one line")
    'only one line'
    >>> normalize_markdown(normalize_markdown("## Prep\\n\\nRinsed.\\n\\n"))
    '## Prep\\n\\nRinsed.'
    >>> normalize_markdown("Potential E \\\\[V] vs. RHE")
    'Potential E [V] vs. RHE'
    >>> normalize_markdown("A literal \\\\[label](not a link)")
    'A literal \\\\[label](not a link)'
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned = "\n".join(line.rstrip() for line in lines).rstrip("\n")
    return _INERT_BRACKET_ESCAPE.sub(r"[\1]", cleaned)

"""The documentation's figures must exist on disk.

Tour screenshots are generated from the guided tour and named after each step's
stable ``slug``. This guards the link between the two: a renamed, removed, or
mistyped screenshot fails here rather than only in the (warnings-as-errors)
Sphinx build.
"""
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
from pathlib import Path

import pytest

DOC = Path(__file__).parent.parent / "doc"
IMAGE_REF = re.compile(r"^```\{(?:figure|image)\}\s+(\S+)", re.MULTILINE)


def _referenced_images() -> list[tuple[Path, str]]:
    return [(page, ref) for page in sorted(DOC.glob("*.md")) for ref in IMAGE_REF.findall(page.read_text())]


def test_doc_pages_reference_images():
    """Guard the guard: a regex that matched nothing would make this file vacuous."""
    assert _referenced_images()


@pytest.mark.parametrize("page,ref", _referenced_images(), ids=lambda v: getattr(v, "name", v))
def test_referenced_image_exists(page: Path, ref: str):
    assert (page.parent / ref).is_file(), f"{page.name} references missing image {ref}"


def test_tour_order_lists_existing_screenshots():
    """The GIF is assembled from this manifest, so a stale entry breaks `tour-gif`."""
    order = DOC / "images" / "tour-order.txt"
    assert order.is_file(), "run `pixi run -e dev screenshots` to generate it"

    frames = order.read_text().split()
    assert frames
    for name in frames:
        assert (DOC / "images" / name).is_file(), f"tour-order.txt lists missing screenshot {name}"

    on_disk = {p.name for p in (DOC / "images").glob("tour-*.png")}
    assert on_disk == set(frames), "screenshots on disk and tour-order.txt disagree"

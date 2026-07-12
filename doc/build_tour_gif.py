"""Assemble doc/images/tour.gif from the tour screenshots, in tour order.

The screenshots are named after their step's stable slug (``tour-yaml-editor.png``)
rather than its position, so a glob no longer sorts them into tour order. The
order is read instead from ``images/tour-order.txt``, written by
``generate_tour_screenshots.py``.

Run via the pixi task: ``pixi run -e dev tour-gif``. Needs ImageMagick 7 (``magick``)
on PATH.
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

import subprocess
import sys
from pathlib import Path

IMAGES = Path(__file__).parent / "images"
ORDER_FILE = IMAGES / "tour-order.txt"
GIF = IMAGES / "tour.gif"


def main() -> None:
    if not ORDER_FILE.exists():
        raise SystemExit(f"{ORDER_FILE} is missing — run `pixi run -e dev screenshots` first")

    frames = [IMAGES / name for name in ORDER_FILE.read_text().split()]
    if missing := [f for f in frames if not f.exists()]:
        raise SystemExit(f"screenshots listed in {ORDER_FILE.name} but missing: {[f.name for f in missing]}")

    cmd = [
        "magick",
        "-delay",
        "220",
        "-loop",
        "0",
        *[str(f) for f in frames],
        "-resize",
        "1100x",
        "-layers",
        "Optimize",
        str(GIF),
    ]
    print(" ".join(cmd))
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()

"""Regenerate doc/images/tour-*.png from the live guided tour.

Steps through every ``TourStep`` in ``AutotagApp``'s guided tour, running each
step's ``on_enter`` exactly as the real tour does, and grabs a screenshot of the
whole window (with the coach-mark bubble and spotlight) after each one.

Each image is named after its step's ``slug`` (``tour-yaml-editor.png``), *not*
its position or title, so that inserting or renumbering a tour step leaves the
file names — and therefore the figures referenced from ``doc/usage.md`` — intact.

Because the names no longer sort into tour order, the step order is written out
separately as ``images/tour-order.txt`` for ``doc/build_tour_gif.py`` to consume.

Run via the pixi task: ``pixi run -e dev screenshots``. Requires
QT_QPA_PLATFORM=offscreen and a real FONTCONFIG_FILE (both set by the task) —
without them Qt silently falls back to a low-quality bitmap font.
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

from pathlib import Path

from PyQt6 import QtCore, QtWidgets

from autotag_metadata.app import AutotagApp

OUT_DIR = Path(__file__).parent / "images"
ORDER_FILE = OUT_DIR / "tour-order.txt"


def _check_slugs(slugs: list[str]) -> None:
    """A missing or duplicated slug would silently drop or overwrite a screenshot."""
    if missing := [i for i, slug in enumerate(slugs) if not slug]:
        raise SystemExit(f"tour steps without a slug (see GuidedTour._build_steps): {missing}")
    if duplicates := {slug for slug in slugs if slugs.count(slug) > 1}:
        raise SystemExit(f"duplicate tour step slugs: {sorted(duplicates)}")


def main() -> None:
    app = QtWidgets.QApplication([])
    win = AutotagApp()
    win.resize(1400, 900)
    win.show()
    app.processEvents()

    tour = win._tour
    tour.start()
    app.processEvents()

    slugs = tour.step_slugs
    _check_slugs(slugs)

    written = []
    for i, slug in enumerate(slugs):
        tour.show_step(i)
        # Flush Qt's deferred-delete queue so cleared/rebuilt panels don't leave
        # stale widgets behind in the grab (plain processEvents() doesn't do this).
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete.value)
        for _ in range(5):
            app.processEvents()
        fname = OUT_DIR / f"tour-{slug}.png"
        win.grab().save(str(fname))
        written.append(fname)
        print(f"saved {fname}")

    ORDER_FILE.write_text("".join(f"{f.name}\n" for f in written))

    # Screenshots of steps that no longer exist would otherwise linger and be
    # swept into the GIF glob / stay referenced from the docs.
    for stale in sorted(set(OUT_DIR.glob("tour-*.png")) - set(written)):
        stale.unlink()
        print(f"removed stale {stale}")

    # The tour never reached its normal finish, so its scratch template/snippet/view
    # entries are still seeded in the config — stop() runs the same cleanup a real
    # "Done" click would (deletes them, restores the user's prior settings).
    tour.stop()
    win.config.save_settings()
    print(f"done, {len(slugs)} steps")


if __name__ == "__main__":
    main()

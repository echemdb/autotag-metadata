"""Config module — persistent application settings and template management."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2024-2026 Johannes Hermann
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

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import toml

if sys.platform == "win32":
    appdata_path: Path = Path(os.environ["APPDATA"]) / "autotag-metadata"
elif sys.platform == "darwin":
    appdata_path = Path.home() / "Library" / "Application Support" / "autotag-metadata"
else:
    appdata_path = Path.home() / ".config" / "autotag-metadata"

templates_path: Path = appdata_path / "templates"
snippets_path: Path = appdata_path / "snippets"
views_path: Path = appdata_path / "views"

if appdata_path.exists() and not appdata_path.is_dir():
    raise FileExistsError("Config path is not a folder.")

templates_path.mkdir(parents=True, exist_ok=True)
snippets_path.mkdir(parents=True, exist_ok=True)
views_path.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


class Config:
    """Persistent application configuration backed by a TOML file."""

    def __init__(self) -> None:
        self._config_path = appdata_path / "config.toml"
        self._config: dict[str, Any]
        if self._config_path.exists():
            with open(self._config_path) as f:
                self._config = toml.load(f)
            logger.info("config file: %s", self._config_path)
            logger.info("template files in %s", templates_path)
        else:
            self._config = {"templates": {}}
        self._config.setdefault("templates", {})
        self._config.setdefault("snippets", {})
        self._config.setdefault("views", {})
        self._prune_missing_entries()

    def _prune_missing_entries(self) -> None:
        """Drop template/snippet/view entries whose backing file is gone.

        A leftover entry (e.g. from a delete whose config write failed) would
        otherwise crash on the next start when its file is read. Pruning heals
        such a config instead of failing.
        """
        sections = {"templates": templates_path, "snippets": snippets_path, "views": views_path}
        removed = False
        for section, base in sections.items():
            for name, filename in list(self._config[section].items()):
                if not (base / filename).exists():
                    logger.warning("dropping %s '%s': file %s is missing", section, name, filename)
                    del self._config[section][name]
                    removed = True
        if removed:
            try:
                self._write_config()
            except OSError as exc:  # best effort; in-memory prune already prevents the crash
                logger.warning("could not rewrite config after pruning: %s", exc)

    # -- property accessors for UI settings --------------------------------

    @property
    def window_geometry(self):
        """Window position/size as a tuple, or ``None``."""
        return self._config.get("windowGeometry")

    @window_geometry.setter
    def window_geometry(self, value):
        self._config["windowGeometry"] = value

    @property
    def watch_folder(self) -> str:
        """Last watched folder path."""
        return self._config.get("watchFolder", "")

    @watch_folder.setter
    def watch_folder(self, value: str):
        self._config["watchFolder"] = value

    @property
    def temporary_file(self) -> str:
        """Path to the temporary YAML file."""
        return self._config.get("temporaryFile", "")

    @temporary_file.setter
    def temporary_file(self, value: str):
        self._config["temporaryFile"] = value

    @property
    def file_patterns(self) -> str:
        """Comma-separated file pattern string."""
        return self._config.get("filePatterns", "")

    @file_patterns.setter
    def file_patterns(self, value: str):
        self._config["filePatterns"] = value

    @property
    def recursive_watching(self) -> bool:
        """Whether to watch subdirectories recursively."""
        return bool(self._config.get("recursiveWatching", False))

    @recursive_watching.setter
    def recursive_watching(self, value: bool):
        self._config["recursiveWatching"] = value

    @property
    def multiview_layout(self) -> dict | None:
        """Serialized tiling layout of the multi-view, or ``None``.

        Falls back to the legacy ``multiviewPaths`` list (rendered as a flat
        horizontal row) for configs written before named layouts existed.
        """
        raw = self._config.get("multiviewLayout")
        if raw:
            return json.loads(raw)
        legacy = self._config.get("multiviewPaths")
        if legacy:
            return _flat_layout(legacy)
        return None

    @multiview_layout.setter
    def multiview_layout(self, value: dict | None):
        self._config["multiviewLayout"] = json.dumps(value) if value else ""
        self._config.pop("multiviewPaths", None)

    @property
    def tour_seen(self) -> bool:
        """Whether the first-run guided tour has been shown/dismissed."""
        return bool(self._config.get("tourSeen", False))

    @tour_seen.setter
    def tour_seen(self, value: bool):
        self._config["tourSeen"] = value

    @property
    def template_names(self) -> list[str]:
        """List of stored template names."""
        return list(self._config.get("templates", {}).keys())

    @property
    def snippet_names(self) -> list[str]:
        """List of stored snippet names."""
        return list(self._config.get("snippets", {}).keys())

    @property
    def view_names(self) -> list[str]:
        """List of stored multi-view layout names."""
        return list(self._config.get("views", {}).keys())

    # -- persistence -------------------------------------------------------

    def save_settings(self) -> None:
        """Write current config to disk."""
        self._write_config()

    def _write_config(self) -> None:
        with open(self._config_path, "w") as f:
            toml.dump(self._config, f)

    # -- template management -----------------------------------------------

    def load_template(self, name: str) -> str:
        """Read and return template content by *name*."""
        return (templates_path / self._config["templates"][name]).read_text()

    def save_template(self, name: str, content: str) -> None:
        """Save *content* as a template under *name*."""
        file_path = templates_path / (name + ".yaml")
        file_path.write_text(content)
        self._config["templates"][name] = name + ".yaml"
        self._write_config()

    def delete_template(self, name: str) -> None:
        """Remove the template *name* and its file (no-op if unknown)."""
        filename = self._config["templates"].pop(name, None)
        if filename is not None:
            # Persist the removal before unlinking, so a failed write never
            # orphans the file (config entry without a file crashes on reload).
            self._write_config()
            (templates_path / filename).unlink(missing_ok=True)

    # -- snippet management -------------------------------------------------

    def load_snippet(self, name: str) -> str:
        """Read and return snippet content (a YAML fragment) by *name*."""
        return (snippets_path / self._config["snippets"][name]).read_text()

    def save_snippet(self, name: str, content: str) -> None:
        """Save *content* as a snippet under *name*."""
        file_path = snippets_path / (name + ".yaml")
        file_path.write_text(content)
        self._config["snippets"][name] = name + ".yaml"
        self._write_config()

    def delete_snippet(self, name: str) -> None:
        """Remove the snippet *name* and its file (no-op if unknown)."""
        filename = self._config["snippets"].pop(name, None)
        if filename is not None:
            # Persist the removal before unlinking, so a failed write never
            # orphans the file (config entry without a file crashes on reload).
            self._write_config()
            (snippets_path / filename).unlink(missing_ok=True)

    def rename_snippet(self, old: str, new: str) -> None:
        """Rename snippet *old* to *new* (no-op if unchanged or unknown)."""
        if old == new or old not in self._config["snippets"]:
            return
        self.save_snippet(new, self.load_snippet(old))
        self.delete_snippet(old)

    # -- multi-view layout management --------------------------------------

    def load_view(self, name: str) -> dict:
        """Read and return a named tiling layout by *name*."""
        return json.loads((views_path / self._config["views"][name]).read_text())

    def save_view(self, name: str, layout: dict) -> None:
        """Save *layout* as a named multi-view under *name*."""
        file_path = views_path / (name + ".json")
        file_path.write_text(json.dumps(layout, indent=2))
        self._config["views"][name] = name + ".json"
        self._write_config()

    def delete_view(self, name: str) -> None:
        """Remove the named view *name* and its file (no-op if unknown)."""
        filename = self._config["views"].pop(name, None)
        if filename is not None:
            # Persist the removal before unlinking, so a failed write never
            # orphans the file (config entry without a file crashes on reload).
            self._write_config()
            (views_path / filename).unlink(missing_ok=True)


def _flat_layout(paths: list[str]) -> dict:
    """Build a layout dict laying *paths* out as a single horizontal row."""
    if len(paths) == 1:
        return {"path": paths[0]}
    return {
        "orientation": "h",
        "sizes": [],
        "children": [{"path": p} for p in paths],
    }

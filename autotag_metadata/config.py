"""Config module — persistent application settings and template management."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2024 Johannes Hermann
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

if appdata_path.exists() and not appdata_path.is_dir():
    raise FileExistsError("Config path is not a folder.")

templates_path.mkdir(parents=True, exist_ok=True)

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
    def template_names(self) -> list[str]:
        """List of stored template names."""
        return list(self._config.get("templates", {}).keys())

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

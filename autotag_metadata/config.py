"""Config module"""
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

import toml

if sys.platform == "win32":
    appdata_path = os.path.join(os.getenv("APPDATA"), "autotag-metadata")
elif sys.platform == "linux":
    appdata_path = os.path.join(os.getenv("HOME"), ".config", "autotag-metadata")

templates_path = os.path.join(appdata_path, "templates")

if not os.path.exists(appdata_path):
    os.mkdir(appdata_path)
    os.mkdir(templates_path)
elif not os.path.isdir(appdata_path):
    raise FileExistsError("Config path is not a folder.")

logger = logging.getLogger(__name__)


class Config:
    "Config class for autotag-metadata"

    def __init__(self) -> None:
        ""
        self._config_path = os.path.join(appdata_path, "config.toml")
        if os.path.exists(self._config_path):
            with open(self._config_path, "r") as f:
                self._config = toml.load(f)
            logger.info("config file: %s", self._config_path)
            logger.info("template files in %s", templates_path)
        else:
            self._config = {"templates": {}}

    def save_settings(self) -> None:
        self._write_config()

    def _write_config(self) -> None:
        ""
        with open(self._config_path, "w") as f:
            toml.dump(self._config, f)

    def load_template(self, name: str) -> str:
        ""
        with open(os.path.join(templates_path, self._config["templates"][name])) as f:
            return f.read()

    def save_template(self, name: str, content: str) -> None:
        ""
        file_path = os.path.join(templates_path, name + ".yaml")

        with open(file_path, "w") as f:
            f.write(content)
        self._config["templates"][name] = name + ".yaml"
        self._write_config()

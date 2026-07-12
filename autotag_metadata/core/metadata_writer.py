"""Metadata file creation — hashing and writing .metadata.yaml sidecar files."""
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

import datetime
import hashlib
import json
import logging
import time
from enum import Enum
from pathlib import Path

from autotag_metadata.core.yaml_utils import dump_yaml, json_default

logger = logging.getLogger(__name__)


class MetadataFormat(str, Enum):
    """Serialization format for the sidecar file, chosen independently of the suffix.

    Subclasses ``str`` so members compare equal to their plain-string value
    (``MetadataFormat.JSON == "json"``) and serialize transparently to TOML/JSON
    and Qt ``userData`` — keeping old string-based config files readable.

    When the minimum supported Python is 3.12+, replace ``(str, Enum)`` with
    ``enum.StrEnum``.
    """

    YAML = "yaml"
    JSON = "json"

    @classmethod
    def from_value(cls, value: object, default: str = "yaml") -> "MetadataFormat":
        """Coerce *value* (a string or member) to a member, falling back to *default*."""
        try:
            return cls(value)
        except ValueError:
            return cls(default)


def hash_file(filename: str, max_retries: int = 5, retry_delay: float = 1.0) -> str | None:
    """Generate sha512 hash of a file.

    Retries up to *max_retries* times when the file is still locked or
    not yet fully written to disk.

    Returns the hex digest string, or ``None`` on failure.
    """
    for attempt in range(1, max_retries + 1):
        try:
            sha512_hash = hashlib.sha512()
            with open(filename, "rb") as file:
                for byte_block in iter(lambda: file.read(4096), b""):
                    sha512_hash.update(byte_block)
            return sha512_hash.hexdigest()
        except (PermissionError, FileNotFoundError) as err:
            if attempt < max_retries:
                logger.warning("Attempt %d/%d — cannot read %s: %s", attempt, max_retries, filename, err)
                time.sleep(retry_delay)
            else:
                logger.error("Failed to hash %s after %d attempts: %s", filename, max_retries, err)
                return None


def write_metadata(
    filepath: str,
    parameters: dict,
    suffix: str = ".metadata.yaml",
    format: MetadataFormat | str = MetadataFormat.YAML,
) -> None:
    """Write *parameters* to ``<filepath><suffix>`` (default ``.metadata.yaml``).

    *format* (a :class:`MetadataFormat` or its string value) selects the serialization
    independently of the suffix: ``"json"`` writes JSON, anything else writes YAML.
    """
    meta_path = filepath + suffix
    with open(meta_path, "w", encoding="utf-8") as metadata_file:
        if format == MetadataFormat.JSON:
            json.dump(parameters, metadata_file, indent=2, ensure_ascii=False, default=json_default)
        else:
            # dump_yaml, not yaml.dump: markdown-valued fields are multi-line strings
            # and must reach the sidecar as readable `|` block literals.
            metadata_file.write(dump_yaml(parameters))
    logger.info("wrote metadata for %s", meta_path)


def build_metadata(filepath: str, parameters: dict) -> dict | None:
    """Enrich *parameters* with timestamp, filename and hash for *filepath*.

    Returns the updated parameters dict, or ``None`` if hashing failed.
    The original dict is modified in-place.
    """
    parameters["time metadata"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    parameters["measurement file name"] = Path(filepath).name

    hash_str = hash_file(filepath)
    if hash_str is None:
        logger.error("Skipping metadata for %s — hashing failed", filepath)
        return None
    parameters["measurement file sha512"] = hash_str
    return parameters

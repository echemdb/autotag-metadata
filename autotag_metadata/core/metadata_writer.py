"""Metadata file creation — hashing and writing .meta.yaml sidecar files."""
# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2021-2022 Johannes Hermann
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

import hashlib
import logging
import os
import time

import yaml

logger = logging.getLogger(__name__)


def hash_file(filename, max_retries=5, retry_delay=1.0):
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


def write_metadata(filepath, parameters):
    """Write *parameters* as YAML to ``<filepath>.meta.yaml``."""
    meta_path = filepath + ".meta.yaml"
    with open(meta_path, "w", encoding="utf-8") as metadata_file:
        yaml.dump(parameters, metadata_file, sort_keys=False, allow_unicode=True)
    logger.info("wrote metadata for %s", meta_path)


def build_metadata(filepath, parameters):
    """Enrich *parameters* with timestamp, filename and hash for *filepath*.

    Returns the updated parameters dict, or ``None`` if hashing failed.
    The original dict is modified in-place.
    """
    import datetime

    parameters["time metadata"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    parameters["measurement file name"] = os.path.split(filepath)[-1]

    hash_str = hash_file(filepath)
    if hash_str is None:
        logger.error("Skipping metadata for %s — hashing failed", filepath)
        return None
    parameters["measurement file sha512"] = hash_str
    return parameters

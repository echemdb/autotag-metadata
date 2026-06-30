"""YAML validation and serialization utilities."""
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

import yaml
from yamllint import linter


def validate_yaml_syntax(text):
    """Check whether *text* is syntactically valid YAML.

    Returns ``None`` if valid, or a ``yamllint.linter.LintProblem``
    describing the first syntax error.
    """
    return linter.get_syntax_error(text)


def parse_yaml(text):
    """Safely parse a YAML string and return the resulting object."""
    return yaml.safe_load(text)


def dump_yaml(data):
    """Serialize *data* to a YAML string."""
    return yaml.dump(data, sort_keys=False, allow_unicode=True)


def dump_yaml_to_file(data, filepath):
    """Write *data* as YAML to *filepath*."""
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(data, f, sort_keys=False, allow_unicode=True)

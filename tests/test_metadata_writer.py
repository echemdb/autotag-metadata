"""Tests for autotag_metadata.core.metadata_writer."""
import hashlib
from unittest.mock import patch

import yaml

from autotag_metadata.core.metadata_writer import build_metadata, hash_file, write_metadata


def test_hash_file_returns_sha512(tmp_path):
    f = tmp_path / "sample.bin"
    content = b"hello world"
    f.write_bytes(content)
    expected = hashlib.sha512(content).hexdigest()
    assert hash_file(str(f)) == expected


def test_hash_file_empty_file(tmp_path):
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    expected = hashlib.sha512(b"").hexdigest()
    assert hash_file(str(f)) == expected


def test_hash_file_not_found_returns_none(tmp_path):
    result = hash_file(str(tmp_path / "nonexistent.txt"), max_retries=1, retry_delay=0)
    assert result is None


def test_write_metadata_creates_sidecar(tmp_path):
    f = tmp_path / "data.csv"
    f.write_bytes(b"a,b,c\n1,2,3")
    params = {"experiment": "test", "value": 42}
    write_metadata(str(f), params)
    meta = tmp_path / "data.csv.meta.yaml"
    assert meta.exists()
    loaded = yaml.safe_load(meta.read_text(encoding="utf-8"))
    assert loaded == {"experiment": "test", "value": 42}


def test_write_metadata_preserves_key_order(tmp_path):
    f = tmp_path / "data.csv"
    f.write_bytes(b"x")
    params = {"z_key": 1, "a_key": 2, "m_key": 3}
    write_metadata(str(f), params)
    content = (tmp_path / "data.csv.meta.yaml").read_text(encoding="utf-8")
    assert content.index("z_key") < content.index("a_key") < content.index("m_key")


def test_build_metadata_adds_required_fields(tmp_path):
    f = tmp_path / "measurement.csv"
    content = b"time,voltage\n0,0.1"
    f.write_bytes(content)
    result = build_metadata(str(f), {})
    assert result is not None
    assert result["measurement file name"] == "measurement.csv"
    assert result["measurement file sha512"] == hashlib.sha512(content).hexdigest()
    assert "time metadata" in result


def test_build_metadata_returns_none_on_hash_failure(tmp_path):
    with patch("autotag_metadata.core.metadata_writer.hash_file", return_value=None):
        result = build_metadata(str(tmp_path / "missing.csv"), {})
    assert result is None


def test_build_metadata_modifies_dict_in_place(tmp_path):
    f = tmp_path / "data.csv"
    f.write_bytes(b"data")
    params = {"key": "val"}
    result = build_metadata(str(f), params)
    assert result is params  # same object modified in place

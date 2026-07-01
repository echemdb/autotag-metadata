"""Integration test: full metadata pipeline without Qt."""
import hashlib

import yaml

from autotag_metadata.core.metadata_writer import build_metadata, write_metadata


def test_full_pipeline(tmp_path):
    """Write a measurement file, build metadata, write sidecar, verify content."""
    data_file = tmp_path / "measurement_001.csv"
    content = b"time,voltage\n0,0.1\n1,0.2\n"
    data_file.write_bytes(content)

    params = {"experiment": "cyclic voltammetry", "operator": "jh"}
    result = build_metadata(str(data_file), params)

    assert result is not None
    write_metadata(str(data_file), result)

    meta_file = tmp_path / "measurement_001.csv.meta.yaml"
    assert meta_file.exists()

    loaded = yaml.safe_load(meta_file.read_text(encoding="utf-8"))
    assert loaded["experiment"] == "cyclic voltammetry"
    assert loaded["operator"] == "jh"
    assert loaded["measurement file name"] == "measurement_001.csv"
    assert loaded["measurement file sha512"] == hashlib.sha512(content).hexdigest()
    assert "time metadata" in loaded

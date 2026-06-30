"""Tests for FileMonitor — real filesystem event detection via watchfiles."""
import hashlib
import threading
import time

import yaml
from PyQt6 import QtCore

from autotag_metadata.core.metadata_writer import build_metadata, write_metadata
from autotag_metadata.file_handling import FileMonitor


def test_monitor_detects_creation_and_produces_metadata(tmp_path):
    """FileMonitor fires create_signal; the full metadata pipeline produces a valid sidecar."""
    content = b"time,voltage\n0,0.1\n1,0.2\n"
    data_file = tmp_path / "measurement.csv"

    monitor = FileMonitor(str(tmp_path))
    received: list[str] = []
    event = threading.Event()

    def on_created(path: str) -> None:
        received.append(path)
        event.set()

    monitor.create_signal.connect(on_created, QtCore.Qt.ConnectionType.DirectConnection)
    monitor.start()
    time.sleep(0.2)  # let watchfiles set up inotify watches before writing

    try:
        data_file.write_bytes(content)
        assert event.wait(timeout=5.0), "FileMonitor did not fire create_signal within 5 s"
        assert received[0] == str(data_file)

        params = {"experiment": "cyclic voltammetry", "operator": "test"}
        result = build_metadata(received[0], params)
        assert result is not None
        write_metadata(received[0], params)

        meta_file = tmp_path / "measurement.csv.meta.yaml"
        assert meta_file.exists()

        loaded = yaml.safe_load(meta_file.read_text(encoding="utf-8"))
        assert loaded["experiment"] == "cyclic voltammetry"
        assert loaded["operator"] == "test"
        assert loaded["measurement file name"] == "measurement.csv"
        assert loaded["measurement file sha512"] == hashlib.sha512(content).hexdigest()
        assert "time metadata" in loaded
    finally:
        monitor.stop()
        monitor.wait()


def test_monitor_detects_modification(tmp_path):
    """FileMonitor fires modify_signal on file modification."""
    data_file = tmp_path / "data.yaml"
    data_file.write_text("x: 1", encoding="utf-8")

    monitor = FileMonitor(str(tmp_path))
    received: list[str] = []
    event = threading.Event()

    def on_modified(path: str) -> None:
        received.append(path)
        event.set()

    monitor.modify_signal.connect(on_modified, QtCore.Qt.ConnectionType.DirectConnection)
    monitor.start()
    time.sleep(0.2)  # let watchfiles set up inotify watches before writing

    try:
        data_file.write_text("x: 2", encoding="utf-8")
        assert event.wait(timeout=5.0), "FileMonitor did not fire modify_signal within 5 s"
        assert str(data_file) in received
    finally:
        monitor.stop()
        monitor.wait()


def test_monitor_pattern_filter_ignores_unmatched_files(tmp_path):
    """FileMonitor with a pattern filter only fires for matching filenames."""
    received: list[str] = []
    csv_event = threading.Event()

    def on_created(path: str) -> None:
        received.append(path)
        csv_event.set()

    monitor = FileMonitor(str(tmp_path), patterns=["*.csv"])
    monitor.create_signal.connect(on_created, QtCore.Qt.ConnectionType.DirectConnection)
    monitor.start()

    try:
        (tmp_path / "ignored.txt").write_text("skip me", encoding="utf-8")
        (tmp_path / "ignored.log").write_text("skip me too", encoding="utf-8")
        time.sleep(0.3)
        assert received == [], f"Pattern filter leaked non-CSV events: {received}"

        (tmp_path / "data.csv").write_bytes(b"a,b\n1,2\n")
        assert csv_event.wait(timeout=5.0), "FileMonitor did not detect .csv file within 5 s"
        assert all(p.endswith(".csv") for p in received), f"Got unexpected paths: {received}"
    finally:
        monitor.stop()
        monitor.wait()

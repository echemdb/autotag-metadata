"""Tests for autotag_metadata.config.Config."""
import pytest

import autotag_metadata.config as config_module
from autotag_metadata.config import Config


def _patch_paths(tmp_path, monkeypatch):
    """Redirect all on-disk config locations into *tmp_path*."""
    monkeypatch.setattr(config_module, "appdata_path", tmp_path)
    for attr, name in [
        ("templates_path", "templates"),
        ("snippets_path", "snippets"),
        ("views_path", "views"),
    ]:
        directory = tmp_path / name
        directory.mkdir(exist_ok=True)
        monkeypatch.setattr(config_module, attr, directory)


@pytest.fixture
def config(tmp_path, monkeypatch):
    """Config instance backed by a temp directory."""
    _patch_paths(tmp_path, monkeypatch)
    return Config()


def test_config_defaults(config):
    assert config.watch_folder == ""
    assert config.temporary_file == ""
    assert config.file_patterns == ""
    assert config.recursive_watching is False
    assert config.window_geometry is None
    assert config.template_names == []


def test_config_watch_folder(config):
    config.watch_folder = "/some/path"
    assert config.watch_folder == "/some/path"


def test_config_recursive_watching(config):
    config.recursive_watching = True
    assert config.recursive_watching is True


def test_config_save_and_load(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    templates.mkdir()
    monkeypatch.setattr(config_module, "appdata_path", tmp_path)
    monkeypatch.setattr(config_module, "templates_path", templates)

    c1 = Config()
    c1.watch_folder = "/data/exp"
    c1.file_patterns = "*.csv,*.dat"
    c1.recursive_watching = True
    c1.save_settings()

    c2 = Config()
    assert c2.watch_folder == "/data/exp"
    assert c2.file_patterns == "*.csv,*.dat"
    assert c2.recursive_watching is True


def test_config_save_template(config):
    config.save_template("my_template", "experiment: cv\nvoltage: 1.5\n")
    assert "my_template" in config.template_names


def test_config_load_template(config):
    content = "key: value\n"
    config.save_template("test_tmpl", content)
    assert config.load_template("test_tmpl") == content


def test_config_snippet_roundtrip(config):
    content = "settings:\n  gain: 3\n"
    config.save_snippet("std-gain", content)
    assert "std-gain" in config.snippet_names
    assert config.load_snippet("std-gain") == content


def test_config_delete_snippet(config):
    config.save_snippet("temp", "a: 1\n")
    config.delete_snippet("temp")
    assert "temp" not in config.snippet_names
    config.delete_snippet("temp")  # no-op, must not raise


def test_config_delete_snippet_persists_to_disk(config):
    # Regression: a delete must remove the entry from config.toml, not just the
    # file, so the next start does not reference a missing file.
    config.save_snippet("gone", "a: 1\n")
    config.delete_snippet("gone")
    reloaded = Config()
    assert "gone" not in reloaded.snippet_names


def test_config_prunes_orphaned_entries_on_load(tmp_path, monkeypatch):
    # Regression: a config entry whose backing file is missing must be pruned on
    # load instead of crashing the next start (load_snippet would raise).
    _patch_paths(tmp_path, monkeypatch)
    (tmp_path / "config.toml").write_text('[templates]\n\n[snippets]\nghost = "ghost.yaml"\n\n[views]\n')
    config = Config()
    assert config.snippet_names == []
    assert "ghost" not in Config().snippet_names  # pruned and persisted


def test_config_view_roundtrip(config):
    layout = {"orientation": "h", "sizes": [100, 200], "children": [{"path": "a"}, {"path": "b"}]}
    config.save_view("compare", layout)
    assert "compare" in config.view_names
    assert config.load_view("compare") == layout


def test_config_delete_view(config):
    config.save_view("temp", {"path": ""})
    config.delete_view("temp")
    assert "temp" not in config.view_names


def test_config_multiview_layout_roundtrip(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    layout = {"orientation": "v", "sizes": [10, 20], "children": [{"path": "x"}, {"path": "y"}]}
    c1 = Config()
    c1.multiview_layout = layout
    c1.save_settings()
    assert Config().multiview_layout == layout


def test_config_multiview_layout_legacy_fallback(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)
    c1 = Config()
    c1._config["multiviewPaths"] = ["a", "b"]
    c1.save_settings()
    layout = Config().multiview_layout
    assert layout == {"orientation": "h", "sizes": [], "children": [{"path": "a"}, {"path": "b"}]}

"""Tests for autotag_metadata.config.Config."""
import pytest

import autotag_metadata.config as config_module
from autotag_metadata.config import Config


@pytest.fixture
def config(tmp_path, monkeypatch):
    """Config instance backed by a temp directory."""
    templates = tmp_path / "templates"
    templates.mkdir()
    monkeypatch.setattr(config_module, "appdata_path", tmp_path)
    monkeypatch.setattr(config_module, "templates_path", templates)
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

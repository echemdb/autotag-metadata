![test status](https://github.com/echemdb/autotag-metadata/actions/workflows/test.yml/badge.svg)

autotag-metadata is a lightweight tool that creates metadata files for newly created files
in the filesystem. A common example is the creation of measurement files during an
experiment, for which you would like to store additional information. The content of the
newly created metadata file is based on a user-defined template.

![basic_usage](https://raw.githubusercontent.com/echemdb/autotag-metadata/main/doc/images/basic_usage.gif)

It is possible to couple autotag-metadata with editors to exploit their advanced
capabilities for verifying the metadata against a schema.

![advanced_usage](https://raw.githubusercontent.com/echemdb/autotag-metadata/main/doc/images/advanced_usage.gif)

Multiple instances of the program can be launched to watch different folders simultaneously.

# Installation

## Windows

Download the latest installer from the
[release section](https://github.com/echemdb/autotag-metadata/releases) and launch the
program from the Start menu.

## From source (all platforms)

[Install pixi](https://pixi.sh/latest/#installation), then:

```sh
git clone https://github.com/echemdb/autotag-metadata
cd autotag-metadata
pixi run autotag-metadata
```

# Development

All environments and tasks are managed with [pixi](https://pixi.sh). Configuration lives
in `pyproject.toml` under `[tool.pixi.*]` — there is no separate `pixi.toml`.

```sh
pixi install   # set up all environments
```

**Common tasks**

| Task | Command |
|------|---------|
| Run the app | `pixi run autotag-metadata` |
| Run tests | `pixi run -e python-312 doctest` |
| Lint | `pixi run -e dev lint` |
| Format | `pixi run -e dev black` |
| Build docs | `pixi run -e dev doc` |
| Package (PyInstaller) | `pixi run -e packaging package` |

Tests run against Python 3.10–3.14. For headless environments set
`QT_QPA_PLATFORM=offscreen`.

**Architecture**

```
autotag_metadata/
    __main__.py          entry point
    app.py               UI controller — thin QMainWindow subclass
    config.py            typed property accessors over a TOML config file
    file_handling.py     filesystem monitoring via watchdog
    core/
        metadata_writer.py   file hashing + .meta.yaml writing (no Qt)
        yaml_utils.py        YAML parse / validate / dump (no Qt)
    ui/
        templatetree.py, template_dialog.py, logger.py, *.ui
tests/
    test_config.py, test_metadata_writer.py, test_yaml_utils.py,
    test_templatetree.py, test_integration.py
```

`core/` modules have no Qt dependency and can be tested without a running application.

Detailed usage instructions are in the
[documentation](https://echemdb.github.io/autotag-metadata).

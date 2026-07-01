# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ["autotag_metadata/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[("README.md", "."),
    ("autotag_metadata/ui/main_window.ui", "autotag_metadata/ui")]
    # distlib (pulled in via desktop_app) enumerates these wrappers at import.
    + collect_data_files("distlib"),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    # Register distlib's resource finder for PyInstaller's frozen importer, else
    # the Windows build crashes on startup. See rthook_distlib.py.
    runtime_hooks=["rthook_distlib.py"],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="autotag-metadata",
    icon="autotag_metadata/autotag_metadata.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

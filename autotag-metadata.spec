# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ["autotag_metadata/__main__.py"],
    pathex=[],
    binaries=[],
    datas=[("README.md", "."),
    ("autotag_metadata/ui/main_window.ui", "autotag_metadata/ui"),
    ("autotag_metadata/ui/template_dialog.ui", "autotag_metadata/ui")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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

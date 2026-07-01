"""PyInstaller runtime hook: teach distlib's resource finder about the frozen importer.

At startup ``desktop_app`` imports ``fix_entry_points``, which imports
``distlib.scripts``. On Windows that module, at import time, loads its launcher
wrappers via ``distlib.resources.finder("distlib")``. distlib's finder registry
is keyed by loader *class* and has no entry for PyInstaller's frozen importer, so
the lookup raises ``DistlibException: Unable to locate finder for 'distlib'`` and
the packaged app crashes before the GUI starts.

``finder("distlib")`` looks the registry up by ``type(distlib.__loader__)`` — the
loader of the distlib package module itself. So we register that exact loader,
not this hook module's ``__loader__`` (which need not be the same object/class in
the runtime-hook exec context). Harmless on platforms where the crashing code
path never runs.
"""

try:
    import distlib
    import distlib.resources

    # Key the registry by the loader distlib's own module carries, since that is
    # exactly what finder("distlib") will look up (type(sys.modules[pkg].__loader__)).
    loader = getattr(distlib, "__loader__", None)
    if loader is not None:
        distlib.resources.register_finder(loader, distlib.resources.ResourceFinder)
except Exception:  # pragma: no cover - best effort; never block startup
    pass

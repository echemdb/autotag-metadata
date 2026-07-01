"""PyInstaller runtime hook: teach distlib's resource finder about the frozen importer.

At startup ``desktop_app`` imports ``fix_entry_points``, which imports
``distlib.scripts``. On Windows that module, at import time, loads its launcher
wrappers via ``distlib.resources.finder("distlib")``. distlib's finder registry
is keyed by loader class and has no entry for PyInstaller's frozen importer, so
the lookup raises ``DistlibException: Unable to locate finder for 'distlib'`` and
the packaged app crashes before the GUI starts.

Registering this hook module's own ``__loader__`` (the frozen importer instance)
keys the registry by that importer's class, so the lookup succeeds. Harmless on
platforms where the crashing code path never runs.
"""

try:
    import distlib.resources

    # register_finder keys the registry by type(loader); __loader__ here is the
    # frozen importer instance, so this registers its class.
    distlib.resources.register_finder(__loader__, distlib.resources.ResourceFinder)
except Exception:  # pragma: no cover - best effort; never block startup
    pass

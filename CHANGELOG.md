# Changelog

## 1.0.0

A robustness release. It removes old designs rather than keeping them
alongside new ones; pin `pymoos2<1` if you need the 0.1 behavior.

### Geodesy is PROJ

- New `pymoos2.geodesy.LocalFrame(lat, lon, projection="utm"|"aeqd", epoch=0)`
  replaces `MOOSGeodesy`. Conversions go through PROJ and are exact to well
  under a micrometer in both directions. `latlon_to_xy` is now `to_xy`,
  `xy_to_latlon` is now `to_latlon`, and batches use `to_xy_many` /
  `to_latlon_many`.
- The UTM zone is fixed by the origin, so x/y stay continuous when a vehicle
  crosses a zone line. Inside the origin's zone the x/y match what C++
  MOOS-IvP apps compute to under a millimeter.
- New: `geodesic` (exact WGS84 distance, bearing, forward point, paths),
  `distortion` and `leg_deviation` (how far a flat frame departs from the
  ground), and `reframe_*` (move points, headings and geometry between frames).
- `pyproj>=3.4` is now a dependency.
- Removed: `MOOSGeodesy`, `ll_to_utm`, `utm_to_ll`, `utm_letter`,
  `xy_to_latlon_moos`, the spherical "local grid" functions
  (`latlon_to_xy_grid`, `xy_to_latlon_grid`), `MOOSGeodesy.distance`, and the
  golden-vector fixture and its C++ generator.
- `rel_ang` and `project_point` moved from `pymoos2.geodesy` to
  `pymoos2.dtos.geometry.planar`.

### Wire and comms

- A reply that does not decode (truncated, corrupted, compressed, unknown
  data type) raises `ValueError` from the decoder and makes the comms thread
  reconnect. Before, it killed the thread silently.
- Mail queued when a send fails is kept and sent after the reconnect.
- A failed handshake no longer leaks its socket; a handshake reply that is
  neither welcome nor rejection is an error.
- Packets with an implausible length are refused. The socket has a 10 s reply
  timeout, so a silent MOOSDB is detected.
- Text fields decode as UTF-8 with `surrogateescape`, so non-UTF-8 bytes from
  C++ apps round-trip unchanged instead of crashing the decoder.
- `notify()` posts numpy scalars as doubles (numpy integers used to become
  strings) and numpy booleans as `"true"`/`"false"`. `None`, lists, dicts
  and other objects raise `TypeError`; an empty variable name raises
  `ValueError`. Before, they were posted as `str(value)`.
- `MOOSCommClient` validates its arguments, refuses a second `start()`, and
  survives `stop()` racing a receive.
- Clock skew is refreshed after every reconnect, not only the first connect.

### Apps

- A missing mission file raises `FileNotFoundError` (it used to run with
  defaults against localhost:9000). `MissionReader(filepath)` requires the path.
- `set_moos_time_warp()` raises `ValueError` outside (0, 400]; an app with a bad
  `MOOSTimeWarp` reports it and runs at warp 1.
- A boolean config value that is neither true nor false returns the default
  instead of `False`.
- Removed `MissionReader.get_config_list()`; use `get_config_lines()` or
  `get_config()`.

### Build and install

- pymoos2 ships a CMake package (`PyMOOS2Config.cmake`, with a version file).
  A tree's top-level `CMakeLists.txt` finds it once with the block that
  `python -m pymoos2 --cmake-block` prints; each app's `CMakeLists.txt` is
  then one call, `pymoos2_add_script_app()` or `pymoos2_add_package_app()`,
  and sits in `src/` like any C++ app.
- Without pymoos2 the configure warns, the two calls do nothing, and the
  rest of the tree builds.
- `cmake --install` is supported for both layouts. Package apps install to
  `<prefix>/lib/pymoos2-apps/<app>/` with a relocatable launcher in
  `<prefix>/bin`.
- Script apps get their `#!` line set to the configured interpreter instead of
  `/usr/bin/env python3`, and are checked with it.
- Package apps no longer carry their own `launcher.sh.in`; the launcher comes
  from pymoos2.
- New example `pFrameMonitor`: a package app with subpackages, packaged data,
  its own tests and install rules. It publishes `FRAME_DISTORTION`.
- `pNodeWatch` uses Python's built-in web server instead of Flask, so the
  examples need nothing beyond pymoos2.
- Removed the `--web` / `-w` flag (open PyPI in a browser) from generated
  and example script apps.

### Packaging

- Brand assets in `pymoos2.assets`: favicon, mark, wordmark and combined
  lockup, used by the `--web` template and `pNodeWatch`, and shown in the
  README.

- Python 3.8 to 3.14, tested against the installed wheel on each.
- Bytecode caches are excluded from the sdist and wheel.
- The `test` extra is `pytest` only.

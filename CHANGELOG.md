# Changelog

## v0.3 - SKINs, Audio, and Self-Healing Catalogue

Jessica v0.3 makes the public download much easier to run and expands the
viewer metadata used by the native Trinity window.

### Added

- SKIN material selection for supported ships.
- Native `_audio2` sound preview events for warp, gate, booster, and related
  client audio.
- A compressed `catalog/catalog.json.gz` metadata catalogue bundled with the
  public source and release zip.
- Launcher catalogue validation and automatic repair when `runtime/catalog.json`
  is missing, corrupt, or contains no SOF assets.
- Automatic catalogue download fallback from GitHub if the bundled compressed
  catalogue is missing.

### Changed

- Normal users no longer need Elysian Eve, ClientSDE, Node.js, or data-sync
  knowledge to start the viewer.
- The animation filter now represents playable authored animation/event/curve
  entries instead of broad no-op controller states.
- The old visible Activate workflow has been removed from the UI.
- The control panel is wider and better aligned for SKIN, animation, weapon,
  and sound controls.

### Notes

- Requires a local EVE Online installation.
- Python 2.7 can be prepared automatically by the launcher.
- Node.js is only needed by maintainers doing an internal metadata rebuild.

## v0.2 - Jessica

Jessica v0.2 is the first public-ready release.

### Added

- Native EVE Trinity viewer launcher.
- Local EVE client discovery and remembered client path.
- Local runtime catalogue generation.
- Searchable catalogue UI with filters.
- Camera orbit, pan, close zoom, and reset controls.
- Real EVE nebula switching.
- Lighting, post-processing, and after-effects toggles.
- Model animation/state selector.
- Stargate-style activation support where a model exposes a known activation
  path.
- Turret and launcher preview selection.
- Max-hardpoint arming for ships.
- Dummy target firing preview.
- Authored beam/projectile, missile-trail, impact, booster, and explosion
  visual paths where supported by the local client assets.
- Public-safe packaging: no EVE client assets, generated catalogue, or client
  binaries are included in source control.

### Notes

- Requires a local EVE Online installation.
- Requires Node.js for first-run catalogue generation.
- Python 2.7 can be prepared automatically by the launcher.

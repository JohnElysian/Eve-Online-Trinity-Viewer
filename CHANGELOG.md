# Changelog

## v0.3.2 - Triglavian Materialization Fix

Jessica v0.3.2 fixes Triglavian structures that could appear invisible in
Material view while still showing in White or Wireframe modes.

### Changed

- Preview loading now advances Trinity controller materialization variables to
  their fully visible state for standalone inspection.
- Threshold Werpost, Damaged Werpost, Malfunctioning Werpost, Entropic
  Disintegrator Werpost, Triglavian Stellar Accelerator, and Triglavian Stellar
  Observatory now render through the Material path instead of relying on
  non-material diagnostic views.
- Static preview renders include controller diagnostics for materialization
  variables, making future visual reports easier to verify.

### Notes

- Requires a local EVE Online installation.
- This release does not include EVE client assets.

## v0.3.1 - Model Animation Enumeration Fix

Jessica v0.3.1 restores the animation picker to a discovery-first model view.

### Changed

- The animation dropdown now lists exposed Trinity animation updater names,
  curve sets, controllers, and controller event handlers discovered on the
  loaded model instead of hiding them behind an overly strict playable filter.
- Duplicate-friendly discovery keeps separately exposed model internals visible
  even when they share a friendly name.
- Stargates and other structured models can expose their authored controller
  and curve entries again for direct inspection.
- Controller event playback now tries the owning controller as well as the
  model node.
- The Activate control is visible again as a separate model utility; the
  animation dropdown itself stays focused on discovered model entries.

### Notes

- Requires a local EVE Online installation.
- This release does not include EVE client assets.

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

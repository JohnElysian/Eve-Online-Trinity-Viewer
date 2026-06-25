# Changelog

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

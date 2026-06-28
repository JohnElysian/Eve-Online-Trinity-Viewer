# Changelog

## v0.4.0 - Search, Charges, And Model Rotation

Jessica v0.4.0 removes the unstable sound-preview experiment and focuses the
public build back on the native visual viewer: fast catalogue search, weapon
charge previews, and cinematic model rotation.

### Added

- Weapon charge selection beneath the Weapon control after arming.
- Exact charge compatibility from EVE dogma charge-group and charge-size data.
- Authored charge colours from `graphicIDs.ammoColor`, bound to Trinity's
  native `Ammo` curve where the firing effect exposes one.
- Missile preview switching from the selected missile charge.
- Model yaw, pitch, and roll controls for turning ships, gates, stations, and
  structures into better screenshot angles.
- Wider search/result support so broad searches can expose the full result set
  without stopping at the old first-page cap.

### Changed

- Sound preview controls have been removed from the public viewer. Native
  firing, explosion, SKIN, nebula, animation, and model inspection visuals stay
  intact; the fragile `_audio2` preview path is no longer exposed.
- The bundled metadata catalogue has been rebuilt with exact weapon charge
  mappings and authored ammo colours.
- Charge selection persists per weapon family instead of snapping back to the
  default charge whenever the model is rearmed.

### Notes

- Requires a local EVE Online installation.
- This release does not include EVE client assets, audio banks, models,
  textures, or binaries.

## v0.3.3 - Native Audio And Explosion Playback

Jessica v0.3.3 fixes native sound playback and restores explosion playback
through the same authored Trinity child-explosion path used by the EVE client.

### Changed

- World/space sound previews now use a model-attached `audio2.AudEmitter`
  before falling back to UI playback.
- Jessica now keeps the native audio listener aligned with the preview camera
  so 3D Wwise events are audible instead of silently attenuated away.
- Weapon audio warmup no longer has an unreachable ready-state branch.
- Explosion playback now follows the client `SpaceObjectExplosionManager`
  pattern: configure child explosion transforms, append the effect to the
  scene, then play the authored `EveChildExplosion` entries.
- Explosion audio curves are preserved and scaled instead of being stripped out
  of the authored effect graph.
- The current local viewer control polish, cinematic sliders, hull damage
  preview, and latest weapon preview improvements are included in the public
  build.

### Notes

- Requires a local EVE Online installation.
- This release does not include EVE client assets.

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

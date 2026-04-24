# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- CI: Add CI pipeline with tests (pytest, coverage ≥ 80%), SCA (pip-audit), and SAST (Bandit + CodeQL)
- Label: Progress bar shows current image index and total count (`X / N`)
- Label: Shortcut legend visible in right panel (← →  ↑ ↓  PgUp/Dn  Enter  Del)
- Label: Tooltips on all buttons with keyboard shortcut hints

### Changed
- Label: Prediction label in dark theme — replaced light background with dark (`#2a2a2a`)
- Label: Renamed button "Update" to "Save & Next" for clearer semantics
- Label: Grid button indicates on/off state via colour (blue = active, grey = inactive)
- Label: Reordered +/− buttons — fine steps (±0.1) on top, coarse steps (±1.0) below
- Label: Visual save feedback — "Save & Next" briefly flashes green after successful save

### Fixed
- Label: Confirmation dialog before permanently deleting an image
- Label: Error handling for `shutil.move()` and `os.remove()` shows error message instead of crashing
- Label: Polar overlay (ticks and labels) with halo effect — visible on both light and dark images (WCAG contrast ≥ 3:1)
- Label: Prevent accidental file overwrite on rename — raises `FileExistsError` if target already exists; state updated only after successful move
- Collect: Escape tab characters in TSV fields to prevent format corruption in `HistoricHashData.txt`
- Collect: Hash history pruned to 30-day retention window to prevent unbounded file growth
- Predict: Convert image to model's expected channel mode (RGB/grayscale) based on input shape
- Predict: Use model's actual input dtype instead of hardcoded `float32` (fixes quantized model support)

## [2.0.3] - 2026-04-21

## [2.0.2] - 2026-04-21

### Added
- Tests: Add test suite with 86% coverage (pytest + pytest-cov)
  - Headless GUI testing via `QT_QPA_PLATFORM=offscreen`
  - Tests for `collect.py`, `hash_manual.py`, `labeling.py`, `predict.py`, `__main__.py`
- Dependencies: Add `PySide6` as UI framework

### Changed
- Label: Migrate UI framework from matplotlib to PySide6
  - New class-based architecture (`LabelingWindow`, `PolarOverlayView`)
  - Polar overlay rendered in viewport coordinates (consistent size regardless of image resolution)
  - Yellow tick marks and labels with dark background for readability on any image
  - Dark theme with styled buttons and slider
  - Replace global variables with instance attributes

### Fixed
- Label: `LabelingWindow` now converts `files` to a Python list so that
  removing images works correctly when a numpy array is passed from `label()`

### Removed
- Dependencies: Remove `matplotlib` and `scipy`


## [1.1.0] - 2025-06-05

### Added
- Collect: Add adjustable image collection root path via `--collectpath`
- Label: Add support for defining `--labeling` and `--labelfile` with different paths simultaneously
- Label: Add support for label file with prediction data (modern CSV format)
  - Legacy format (index + file path only) is still supported
- Label: Show prediction value from label file when no model is selected
- App: Add application version handling
  - Version source: `collectmeteranalog/__version__.py`
  - New `--version` parameter
  - Version injected automatically into build processes and GUI window title
  - Version used in GitHub Actions for build artifacts

### Changed
- Collect: Refactor and streamline `readimages` function
- Collect: Save downloaded JPEG images without re-encoding to preserve original quality
- Label: Refactor model prediction functions (`load_interpreter`, `predict`)
- Label: Refactor GUI button alignment and sizing
- App: Update GitHub Actions workflows
- App: Update README

### Fixed
- Collect: Fix image download counter
- Collect: Fix `--keepdownloads` option — no longer deletes `raw_images` content
- App: Fix `exit(1)` on unknown error

### Removed
- Label: Remove bundled internal model — no model is used by default


## [1.0.14]

### Fixed
- Collect: Fix OS-specific download issues


## [1.0.8]

### Fixed
- Label: Fix crash when multiple images referenced in CSV file are not available


## [1.0.1] - 2022-09-18

### Changed
- App: Update release action
- App: Fix requirements

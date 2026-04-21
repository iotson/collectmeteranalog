# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

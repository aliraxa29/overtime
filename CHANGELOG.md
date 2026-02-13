# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation for GitHub open-source release
- CONTRIBUTING.md guide for contributors
- CODE_OF_CONDUCT.md (Contributor Covenant)
- SECURITY.md policy for vulnerability reporting
- GitHub issue and pull request templates
- GitHub Actions CI workflow for automated testing

### Changed
- Updated LICENSE to proper MIT format
- Improved README with badges and contributor information

## [1.0.0] - 2024-XX-XX

### Added
- **Core Overtime Calculation**
  - Automatic overtime calculation on Attendance submit via `doc_events` hook
  - Support for overnight shifts (shifts crossing midnight)
  - Configurable minimum overtime threshold
  - Maximum daily overtime cap

- **Shift Rule System**
  - Weighted shift rule matching (period → category → shift type → department)
  - Support for Standard and Ramadan period rules
  - Religion-based employee categories (Muslim/Non-Muslim/All)
  - Department-specific rule support

- **Ramadan Mode**
  - Date-range activation for Ramadan schedules
  - Separate shift rules for Muslim and Non-Muslim employees
  - Suhoor break support

- **Break & Grace Period Support**
  - Configurable food/suhoor break deductions
  - Grace period for late arrival / early departure
  - Break type configuration (Regular/Suhoor)

- **Rounding Options**
  - No Rounding
  - Round Up
  - Round Down
  - Round to Nearest
  - Configurable rounding interval in minutes

- **Rate Multipliers**
  - Default overtime rate multiplier (e.g., 1.5x)
  - Holiday overtime rate multiplier (e.g., 2.0x)

- **Workflow Features**
  - Optional approval workflow for overtime entries
  - Auto-create overtime entry on attendance submit
  - Bulk recalculation API
  - Daily scheduler fallback job

- **Integration**
  - Attendance sync (overtime hours and entry link)
  - Employee custom fields (religion_category)
  - Salary Slip integration

- **DocTypes**
  - Overtime Settings (Single DocType for global configuration)
  - Overtime Shift Rule (Define shift schedules and rules)
  - Overtime Entry (Individual overtime records)

### Fixed
- Overnight shift duration calculation across midnight
- Checkin record retrieval with fallback search

### Security
- All API methods require authentication
- Respects Frappe's permission system

---

## Version History Format

Each version section should include:

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes

[Unreleased]: https://github.com/aliraxa29/overtime/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/aliraxa29/overtime/releases/tag/v1.0.0

# Changelog

All notable public changes are recorded here.

## 7.4.5

- Preserved caller-visible installer paths across macOS `/private` symlinks and Windows 8.3 temporary-path aliases while retaining canonical safety checks.

## 7.4.4

- Fixed GitHub Actions portability by using the supported `github.workspace` context for the cross-platform Matplotlib cache path.

## 7.4.3

- Hardened CLI output and subprocess decoding for UTF-8 on Windows, redirected pipes, and embedded runners.
- Expanded CI to the full Python 3.10/3.12 matrix on Ubuntu, macOS, and Windows with exact dependency pins.
- Added repository structure/version/CLI verification and a 30% coverage regression baseline with uploaded XML reports.
- Added a dependency-free CycloneDX-style SBOM and GitHub build-provenance attestation to tagged releases.
- Enriched the offline quickstart with one-at-a-time ±10% sensitivity scenarios and an SVG allocation chart.

## 7.4.2

- Added a dependency-free synthetic quickstart that generates input, state, model-card, result, and SHA-256 manifest artifacts in one command.
- Added a cross-platform installer smoke test for Ubuntu, macOS, and Windows, and made CI encoding explicit with `PYTHONUTF8=1`.
- Added two regression tests covering budget conservation and safe demo-directory handling.
- Added a five-minute README entry point and documented the portable-install smoke check.

## 7.4.1

- Fixed portable-payload self-checks by making Codex-only metadata optional and adding an installed-package doctor regression test.
- Updated GitHub Actions to the current Node 24-compatible action majors and added issue/PR templates, CODEOWNERS, Dependabot, and a code of conduct.

## 7.4.0

- Added cross-Agent Skills installation guidance for Codex, Claude Code, Cursor, VS Code/Copilot, OpenCode, and generic compatible clients.
- Added the safe `scripts/install_skill.py` installer and regression tests for destination resolution, payload copying, and overwrite protection.
- Expanded the README with architecture, observable artifacts, example prompts, runtime requirements, engineering trade-offs, and project scope.
- Refined the README to present these capabilities as user-facing engineering design highlights.

## 7.3.5

- Clarified that the public-release contributor listing covers only `xu-chenghao413`'s additions, refactoring, cleanup, tests, and release maintenance, while historical authors remain governed by the license and provenance records.

## 7.3.4

- Reworked the README to foreground `xu-chenghao413`'s public-release contributions, upstream attribution boundaries, and authorized `nature-*` installation routes.

## 7.3.3

- Clarified mixed historical/public-release copyright attribution without removing the original MIT notice.

## 7.3.2

- Pointed README badges and installation examples to the maintainer's public repository.

## 7.3.1

- Updated the CUMCM AI-use baseline to the official 2026 trial rules effective 2026-09-01.
- Recorded the official pre-reference AI declaration wording and supporting `AI工具使用详情.pdf` requirements.

## 7.3.0

- Added Autopilot delivery, persistent source/evidence/artifact state, deterministic validation and versioned packaging.
- Added adaptive page budgeting, novelty evidence, algorithm-claim consistency checks and key-event AI disclosure.
- Added a minimum-change contract for revising an existing manuscript.
- Replaced the unlicensed third-party CUMCM class with an independently authored `ctexart` assembly template.
- Removed private manuscript cases, user-provided page-by-page observations and copied/binary template assets from the public distribution.
- Separated official competition rules from intentionally stricter maintainer policies.
- Added provenance, third-party, contribution and security documentation.

## 6.1.0

- Added competition rule baselines, submission metadata guards, preflight checks and automated validation.

## 6.0.0 and earlier

- Introduced Codex plugin packaging, cross-harness state, multi-competition routing, weighted scoring and the original staged workflow.

Earlier implementation details remain available through the cleaned Git history. Removed third-party or private artifacts are intentionally not preserved in public tags.

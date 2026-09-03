# Provenance and publication policy

This file defines what may enter the public repository. It is a maintenance record, not a statement that linked third-party material is open licensed.

## Public artifacts

| Artifact | Public basis | Publication rule |
|---|---|---|
| Source code and tests | Public-release additions and modifications are independently authored; historical portions retain their file-level notices | MIT unless the file states otherwise; see [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md) |
| `templates/latex/*/main.tex` | Public-release assembly templates with preserved historical attribution where present | MIT for public-release additions; keep SPDX headers and do not paste third-party classes |
| `competitions/cumcm/empirical.json` | Aggregate descriptive measurements from 91 located documents; 59 yielded extractable text | Publish aggregate fields only; do not publish PDFs, extracted text, filenames tied to private users, or sentence corpora |
| `distilled_formats.md`, `distilled_naming.md`, `distilled_structures.md` | Independently rewritten summaries of aggregate observations | Keep only general patterns and sample-size limitations; never include copied passages |
| `phrase_bank.md` and other phrase banks | Maintainer-authored generic writing scaffolds | Must be clean-room wording; do not reconstruct or paraphrase identifiable source sentences |
| Competition rule baselines | Links and maintainer summaries of official pages | Record URL and verification date; official source controls |

The public-release contribution boundary and the historical `mathmodel-skill` lineage are documented in [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md). Separately installed `nature-*` packages remain external dependencies; this repository records their conceptual influence and runtime routing only, not their source or redistribution rights.

## Material excluded from publication

- Source-paper PDFs, OCR/text dumps, screenshots and paid downloads.
- User-provided papers, private datasets, review correspondence, scores and iteration logs.
- Page-by-page observations from user-provided collections unless the owner has explicitly authorized public release.
- Third-party LaTeX classes, example manuals and compiled PDFs without a compatible redistribution license.
- Source files from separately installed `mcm`, `nature-*`, or other skills.
- Credentials, personal identifiers, team identifiers and generated contest workspaces.

Excluded material belongs outside the repository. `.gitignore` is only a backstop; maintainers must also inspect staged files and Git history.

## Source register

| Source family | Purpose | Redistribution status |
|---|---|---|
| CUMCM official website and current rules links | Competition compliance | Link and summarize only; not relicensed |
| China College Students Online public paper gallery | Aggregate layout/text measurements | Do not redistribute source documents or extracted passages |
| Public GitHub paper indexes named in `competitions/cumcm/empirical_notes.md` | Aggregate measurements and source discovery | Each upstream item retains its own terms |
| COMAP official rules and judging guidance | MCM/ICM baseline | Link and summarize only |
| Diangong Cup official pages | Competition baseline | Link and summarize only |

## Adding a new source

Before committing any derived artifact, record:

1. Exact source URL or owner-provided origin.
2. Access date and license/permission status.
3. Whether raw material may be redistributed.
4. Transformation method and output fields.
5. Evidence that the public artifact contains no copied passage or private identifier.
6. Human reviewer and review date.

If permission is unclear, keep the source and its derived case notes private. Acknowledgement alone is not permission.

## Summary

<!-- What changed and why? Keep the change focused. -->

## Validation

- [ ] `uv sync --locked --extra dev`
- [ ] `uv run python -m unittest discover -s tests -v`
- [ ] `uv run python scripts/doctor.py --skip-tools`
- [ ] `uv run python scripts/validate_eval.py --list-cases` (when behavior/tooling changes)
- [ ] I added or updated behavioral tests for script/tooling changes.
- [ ] I updated documentation or changelog when the public behavior changed.

## Provenance and privacy

- [ ] Any external source, transformation, and permission status are recorded in `PROVENANCE.md`.
- [ ] No credentials, private paths, unpublished manuscripts, source-paper PDFs, copied passages, or unlicensed templates are included.
- [ ] Competition rules are clearly labeled as official sources or maintainer heuristics.

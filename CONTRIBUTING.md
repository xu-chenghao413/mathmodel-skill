# Contributing

Contributions are welcome when they preserve reproducibility, provenance and competition-rule boundaries.

## Before opening a pull request

1. Do not add paper PDFs, extracted paper passages, private team material, credentials or third-party templates without a compatible license.
2. Record new external sources and transformations in `PROVENANCE.md`.
3. Label maintainer heuristics as heuristics; do not present them as official competition rules.
4. Keep `SKILL.md` concise and route detailed conditional procedures through `references/`.
5. Add or update behavioral tests for script changes.

Run:

```bash
python -m unittest discover -s tests -v
python scripts/doctor.py
```

By contributing, you confirm that you have the right to submit the contribution under the repository's MIT License.


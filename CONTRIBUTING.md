# Contributing

Contributions are welcome when they preserve reproducibility, provenance and
competition-rule boundaries. See [`GOVERNANCE.md`](./GOVERNANCE.md) for the
current maintainer and merge policy.

## Development setup

```bash
uv sync --locked --extra dev
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run python scripts/verify_project.py --check-cli --require-yaml
uv run ruff check --select E9,F63,F7,F82 scripts examples templates/shared/code_starter
```

## Pull request checklist

1. Do not add paper PDFs, extracted passages, private team material,
   credentials or third-party templates without a compatible license.
2. Record external sources, transformations and permissions in
   [`PROVENANCE.md`](./PROVENANCE.md).
3. Label maintainer heuristics as heuristics; never present them as official
   competition rules.
4. Keep `SKILL.md` focused; route conditional detail through `references/`.
5. Add behavioral tests and, when the change affects agent behavior, update a
   contract case under `evals/cases/`.
6. Update the changelog for user-visible behavior or schema changes.

Use synthetic fixtures, explain the reproduction, and keep the PR narrowly
scoped. Maintainers merge only after CI and the public-surface checks pass.

By contributing, you confirm that you have the right to submit the contribution
under the repository's MIT License.

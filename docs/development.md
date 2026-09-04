# Development

The supported development matrix is Python 3.10, 3.11 and 3.12 on Ubuntu,
macOS and Windows. Use `uv` for a locked environment:

```bash
uv sync --locked --extra dev
uv run python -m unittest discover -s tests -p "test_*.py" -v
uv run python scripts/verify_project.py --check-cli --require-yaml
uv run ruff check --select E9,F63,F7,F82 scripts examples templates/shared/code_starter
```

The modeling runtime profile in `templates/shared/requirements.txt` is
deliberately broader and uses compatibility ranges because clients may only
need a subset. `pyproject.toml` and `uv.lock` describe the reproducible
development and verification environment; they are not a claim that every
optional LaTeX or solver tool is bundled.

Before a pull request, run the offline quickstart and all three contract cases:

```bash
uv run python examples/quickstart/run_demo.py --output demo-output
uv run python scripts/validate_eval.py --case cumcm_autopilot_blocked
uv run python scripts/validate_eval.py --case mcm_guided_confirmation
uv run python scripts/validate_eval.py --case diangong_delivery_gate
```

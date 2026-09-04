# Agent evaluations

`evals/cases/` is a small, deterministic contract suite. It tests safety and
workflow invariants that can be observed across Codex, Claude Code, Cursor,
Copilot, OpenCode and other clients. It does not score prose style or claim a
particular model is intelligent.

Each case contains an expected competition, mode, state shape, required
blockers/events, optional artifacts and forbidden claims. The embedded fixture
is a smoke test. For a real run, provide the workspace state and a JSON/JSONL
event transcript:

```bash
python scripts/validate_eval.py --case cumcm_autopilot_blocked \
  --workspace ./team-workspace --transcript ./qa/run.jsonl --json
```

Keep transcripts synthetic or scrubbed before committing them. Never add
problem PDFs, private data, credentials or team-identifying text to fixtures.

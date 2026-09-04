# Agent contract evaluations

This directory contains small, provider-agnostic contract tests for the public
skill. They validate observable invariants that every compatible agent should
preserve:

- the competition and interaction mode are explicit;
- missing evidence creates a visible blocker instead of an invented result;
- guided runs request confirmation at a consequential decision;
- a delivery gate is reported only when the required artifact set is present.

These are not a leaderboard or a claim about model intelligence. They are a
deterministic harness for recorded runs and synthetic regression fixtures. A
real transcript can be checked with:

```bash
python scripts/validate_eval.py --case cumcm_autopilot_blocked \
  --workspace path/to/workspace --transcript run.jsonl
```

List available contracts with `python scripts/validate_eval.py --list-cases`.
Case files are intentionally sanitized and contain no contest papers or team
material.

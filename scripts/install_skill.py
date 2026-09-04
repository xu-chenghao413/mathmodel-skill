#!/usr/bin/env python3
"""Install the portable mathmodel-skill payload into a supported agent directory.

The installer deliberately copies the complete runtime payload (SKILL.md,
references, competition packs, templates, config, and executable helpers),
but excludes Git metadata, CI files, tests, and generated workspaces.
It refuses to overwrite an existing destination; use ``git pull`` for a
checkout-based upgrade or remove the destination only after reviewing it.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    from scripts.console import configure_stdio
except ImportError:
    from console import configure_stdio


SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "mathmodel-skill"

PROJECT_AGENT_DIRS = {
    "codex": Path(".agents") / "skills",
    "claude": Path(".claude") / "skills",
    "cursor": Path(".cursor") / "skills",
    "copilot": Path(".github") / "skills",
    "opencode": Path(".opencode") / "skills",
    "generic": Path(".agents") / "skills",
}

USER_AGENT_DIRS = {
    "codex": Path(".agents") / "skills",
    "claude": Path(".claude") / "skills",
    "cursor": Path(".cursor") / "skills",
    "copilot": Path(".copilot") / "skills",
    "opencode": Path(".config") / "opencode" / "skills",
    "generic": Path(".agents") / "skills",
}

RUNTIME_FILES = (
    "SKILL.md",
    "AGENTS.md",
    "LICENSE",
    "PROVENANCE.md",
    "THIRD_PARTY_NOTICES.md",
)
RUNTIME_DIRS = (
    "competitions",
    "config",
    "references",
    "scripts",
    "templates",
)


def resolve_destination(
    agent: str,
    scope: str,
    destination: str | None = None,
    *,
    home: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    """Resolve the destination directory for an agent and install scope."""
    if destination:
        return Path(destination).expanduser().resolve()
    if agent not in PROJECT_AGENT_DIRS:
        raise ValueError(f"unsupported agent: {agent}")
    if scope not in {"project", "user"}:
        raise ValueError(f"unsupported scope: {scope}")
    base = (cwd or Path.cwd()) if scope == "project" else (home or Path.home())
    mapping = PROJECT_AGENT_DIRS if scope == "project" else USER_AGENT_DIRS
    return (base / mapping[agent] / SKILL_NAME).resolve()


def _assert_safe_destination(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if destination == source or source in destination.parents:
        raise ValueError(
            "destination must not be the skill source or a child of the source "
            "checkout"
        )


def install_payload(source: Path, destination: Path) -> list[Path]:
    """Copy the runtime payload and return the paths created under destination."""
    source = source.resolve()
    # Keep the caller's lexical destination for returned paths.  macOS may
    # expose /var through /private and Windows may expose TEMP through an 8.3
    # alias; canonicalize only for safety checks, not for API-visible paths.
    destination = destination.expanduser()
    resolved_destination = destination.resolve()
    if not (source / "SKILL.md").is_file():
        raise FileNotFoundError(f"missing skill entrypoint: {source / 'SKILL.md'}")
    _assert_safe_destination(source, resolved_destination)
    if destination.exists():
        raise FileExistsError(
            f"destination already exists: {destination}; refusing to overwrite"
        )

    missing_files = [source / name for name in RUNTIME_FILES if not (source / name).is_file()]
    missing_dirs = [source / name for name in RUNTIME_DIRS if not (source / name).is_dir()]
    if missing_files or missing_dirs:
        missing = ", ".join(str(path) for path in (*missing_files, *missing_dirs))
        raise FileNotFoundError(f"missing runtime payload: {missing}")

    destination.mkdir(parents=True)
    created: list[Path] = []
    for filename in RUNTIME_FILES:
        source_file = source / filename
        target_file = destination / filename
        # Copy content without propagating read-only checkout attributes.
        shutil.copyfile(source_file, target_file)
        created.append(target_file)
    for dirname in RUNTIME_DIRS:
        source_dir = source / dirname
        target_dir = destination / dirname
        shutil.copytree(source_dir, target_dir, copy_function=shutil.copyfile)
        created.extend(path for path in target_dir.rglob("*") if path.is_file())
    return created


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install mathmodel-skill into a project or user Agent Skills directory."
    )
    parser.add_argument(
        "--agent",
        choices=tuple(PROJECT_AGENT_DIRS),
        default="generic",
        help="target agent directory convention (default: generic/.agents)",
    )
    parser.add_argument(
        "--scope",
        choices=("project", "user"),
        default="project",
        help="project-local or user-level installation (default: project)",
    )
    parser.add_argument(
        "--destination",
        help="explicit destination directory; overrides --agent and --scope",
    )
    parser.add_argument(
        "--source",
        default=str(SKILL_ROOT),
        help="skill checkout to install (default: this checkout)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.source).expanduser().resolve()
    try:
        destination = resolve_destination(
            args.agent,
            args.scope,
            args.destination,
        )
        created = install_payload(source, destination)
    except (FileExistsError, FileNotFoundError, ValueError, OSError) as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 2

    print(f"installed {SKILL_NAME} to {destination}")
    print(f"copied {len(created)} runtime files")
    print("restart or reload the agent, then invoke the skill by its name")
    return 0


if __name__ == "__main__":
    configure_stdio()
    raise SystemExit(main())

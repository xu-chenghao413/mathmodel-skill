# Release checklist

1. Update the version in the plugin manifest, `SKILL.md`, `AGENTS.md`, both
   READMEs, `pyproject.toml` and `CHANGELOG.md`.
2. Run `uv lock`, `uv sync --locked --extra dev`, the full tests, Ruff, the
   quickstart and `verify_project.py`.
3. Review `git diff --check`, staged files, provenance and the public surface.
4. Create an annotated tag matching the version, for example:

   ```bash
   git tag -a v7.4.6 -m "mathmodel-skill v7.4.6"
   git push origin main v7.4.6
   ```

5. The tag-triggered release workflow rebuilds the source archive, SHA-256
   checksum and CycloneDX SBOM, then creates the GitHub release and an artifact
   attestation. Consumers can verify a downloaded archive with `sha256sum -c`
   and, when GitHub CLI supports it, `gh attestation verify`.

Never move private contest inputs or separately installed skills into the
release archive. The archive contains the public implementation only.

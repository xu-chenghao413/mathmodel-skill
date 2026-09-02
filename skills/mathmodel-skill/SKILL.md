---
name: mathmodel-skill
description: Plugin shim for mathmodel-skill. Use for CUMCM, MCM/ICM, Diangong Cup, 建模、数模、竞赛论文、模型求解、统计与稳健性、论文/PDF 交付，或用户给出赛题并要求一键生成单文件夹可复现交付包。
---

# mathmodel-skill plugin shim

This wrapper exists so Codex plugins can discover the skill from the official `./skills/` plugin layout.

Before doing any work, read `../../SKILL.md` and treat it as the primary workflow. Resolve `references/`, `competitions/`, `templates/`, `scripts/`, and `config/` relative to `../..`.

Do not duplicate workflow rules here; the root `SKILL.md` is the source of truth.

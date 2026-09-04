# Scripts 工具说明

本目录脚本按"运行时" vs "离线一次性"分两类。

## `install_skill.py` — 跨 Agent 安装器

从公开版 checkout 安全复制运行时 payload 到 Codex、Claude Code、Cursor、VS Code/Copilot 或 OpenCode 的 skill 目录。默认拒绝覆盖已有目录；升级已有 checkout 时请在目标目录执行 `git pull`，不要让安装器静默覆盖本地改动。

```bash
python /path/to/mathmodel-skill/scripts/install_skill.py \
  --source /path/to/mathmodel-skill \
  --agent claude --scope project
python /path/to/mathmodel-skill/scripts/install_skill.py \
  --source /path/to/mathmodel-skill \
  --agent codex --scope user
python /path/to/mathmodel-skill/scripts/install_skill.py \
  --source /path/to/mathmodel-skill \
  --destination /path/to/skills/mathmodel-skill
```

安装器会保留 `SKILL.md`、`references/`、`competitions/`、`templates/`、`scripts/` 和 `config/`，排除 `.git`、CI、测试和生成中的用户工作区；相对路径仍以 skill 根目录为基准。

安装后的便携 payload 可以直接运行 `python scripts/doctor.py --skip-tools`。Codex 的 `agents/openai.yaml`、`.codex-plugin/plugin.json` 和 plugin shim 属于可选元数据；在完整源码 checkout 中如需强制检查它们，可运行 `python scripts/doctor.py --require-codex --skip-tools`。

### `verify_project.py` — 发布前结构与 CLI 校验

检查必需目录、JSON/YAML 语法、版本号一致性，并可对公共 CLI 运行 `--help`：

```bash
python scripts/verify_project.py --check-cli --require-yaml
```

### `build_sbom.py` — 源码 SBOM

按文件生成带 SHA-256 哈希的 CycloneDX 风格 SBOM；Release workflow 会把它作为发布资产，并对源码归档生成 GitHub 构建证明。

### `smoke_install.py` — 跨平台安装冒烟检查

在临时目录安装完整 payload，确认运行时文件存在、CI/测试/用户 state 没有被复制，并运行一次便携版 `doctor.py`。GitHub Actions 会在 Ubuntu、macOS 和 Windows 上执行它：

```bash
python scripts/smoke_install.py
```

---
---

## 运行时脚本 (各 stage 调用)

### `bootstrap_run.py` — Autopilot / Guided 工作区初始化

**调用时机**: Stage 0；已有 state 用 `--resume`，不会覆盖。

```bash
python scripts/bootstrap_run.py --workspace cwd --mode autopilot \
  --competition auto --problem problem.pdf --attachment data.xlsx
```

建立 v4.2 state、标准交付目录、source packet 哈希和竞赛推断；CUMCM 同时初始化 2026 合规状态和关键事件级 AI 使用日志。无法锁定模板或缺必要文件时返回非零并写 blocker。

### `plan_paper_budget.py` — CUMCM 自适应页数预算

**调用时机**: Stage 8 写正文之前。摘要、官方正文和附录三账分开；官方正文按 compact/balanced/dense 或显式目标预算，小问按六维证据负担动态分配。

```bash
python scripts/plan_paper_budget.py --input cwd/analysis/page_budget_input.json \
  --output cwd/analysis/page_budget.json
```

目标不在 26–28 页硬性区间内、输入评分无效或核心篇幅不足时非零退出。附录始终 `completeness_driven` 且不设页数上限。

### `score_artifact.py` — L1 Critic 输出处理
**调用时机**: 每个 stage 结尾
**输入**: critique JSON (Claude L1 critic 输出) + stage_id
**输出**: 写入 `cwd/state/decision_log.json` 的 scores/iterations 字段, 决定下一步 (next_stage / section_patch / carryover / halt)

```bash
python scripts/score_artifact.py --stage 5 --critique state/critique_v0.json
# 路径协议: 默认 cwd/state/decision_log.json, 可用 MATHMODEL_STATE_DIR env var 覆盖
```

### `extract_diff.py` — Section-level patch 生成器
**调用时机**: L1 verdict == "refine" 时
**输入**: artifact 路径 + critique JSON
**输出**: section-level patch 精修 prompt (省 60% token vs 重生成全文)

```bash
# 生成 prompt
python scripts/extract_diff.py --artifact a.md --critique c.json --mode section --output prompt.txt
# 应用 LLM 返回的 patch
python scripts/extract_diff.py --artifact a.md --apply patch.txt --mode section > a_v1.md
```

### `render_paper.py` — Markdown → 竞赛 LaTeX 模板 → PDF
**调用时机**: stage 8 末尾 / stage 9 编译终稿
**输入**: 含分节 .md 的 workspace 目录（MCM/电工杯 10 个；CUMCM 2026 为 11 个，增加 AI 声明）
**输出**: paper.pdf (xelatex 三编)

```bash
python scripts/render_paper.py --workspace cwd/paper_workspace/ --output-dir cwd/paper_output/
# 优先用 pandoc (需独立安装), 失败回退手工正则
```

### `validate_delivery.py` — 最终交付机械门

**调用时机**: Stage 9 最后；科学与视觉 QA 完成之后。

```bash
python scripts/validate_delivery.py --workspace cwd
```

检查最终 PDF/TeX/BibTeX、`src/run_all.*`、环境、结果、图表、复现/统计/引用/算法声明一致性/页结构/视觉/评审 QA 和占位符，生成 `qa/delivery_validation.json` 与 `DELIVERY_MANIFEST.md`。非零退出码不得标记 submission-ready。

### `build_ai_disclosure.py` — CUMCM 2026 AI 使用详情

从真实填写的 `qa/ai_usage_log.json` 生成 `AI 工具使用详情.tex/pdf`；新 schema 按关键实质事件聚合同一目的多轮，记录提示/输出摘要、团队决定、人工修改、核验与影响文件，不导出完整聊天。缺工具版本、用途、关键过程、采纳修改或核验记录时失败；旧四字段用途记录仍可渲染。

```bash
python scripts/build_ai_disclosure.py --log cwd/qa/ai_usage_log.json \
  --output cwd/qa/AI工具使用详情.pdf
```

### `package_delivery.py` — 单文件夹版本化交付

三竞赛 Stage 9 最后运行，每次新建版本化文件夹且不覆盖旧包。CUMCM 分支额外把 `01_正式提交/` 与内部复现留档严格分开，并生成支撑材料 ZIP、本地 MD5/SHA-256、2026 合规报告和 package manifest。未获得参赛队人工确认时仍生成候选包，但保留 `NOT_SUBMISSION_READY.md` 并返回非零。

```bash
python scripts/package_delivery.py --workspace cwd \
  --commitment current-year-commitment.pdf --number-page current-year-number-page.pdf
```

---

## 离线一次性脚本 (skill 维护期使用, 不在运行时跑)

### `ingest_papers.py` — 91 篇 PDF 离线烘焙 → empirical_distribution.md
**调用时机**: skill 安装后一次性运行 / 添加新 PDF 后增量更新
**输入**: `references/papers/` 下 91 篇真国赛 PDF
**输出**: `references/empirical_distribution.md` (字数/章节/图表/公式实测分位数)

```bash
python scripts/ingest_papers.py --papers-dir references/papers/ --output references/empirical_distribution.md
```

烘焙后的 markdown 在运行时被 L1 critic 读取；字数/图表/公式 p25/p50/p75 只作描述性先验，不是配额或硬阈值。

---

## 路径协议总览

| 类型 | 位置 | env var 覆盖 |
|------|------|-------------|
| skill 内静态资源 | `<skill>/{references, templates, scripts}` | 无 |
| 用户 state | `cwd/state/decision_log.json` | `MATHMODEL_STATE_DIR` (兼容 `CUMCM_STATE_DIR`) |
| 用户产物 | `cwd/{analysis,src,results,figures,paper_workspace,paper_output,support_materials,qa,delivery}` | 无 (固定) |

`cwd` = Claude Code 启动时的工作目录 (用户的项目目录)。
`<skill>` = skill 安装目录 (即本 README 所在目录的父目录)。

---

## 单元测试 fixture

L1 critic schema 验证的测试样本在 `<skill>/tests/fixtures/`:
- `test_critique_good.json` — 应通过校验 (verdict=pass)
- `test_critique_bad_keys.json` — 应触发 dim key 白名单 FAIL

```bash
PYTHONIOENCODING=utf-8 python scripts/score_artifact.py --stage 1 \
    --critique tests/fixtures/test_critique_good.json
```

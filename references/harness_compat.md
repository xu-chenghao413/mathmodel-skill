# Harness 兼容协议 (跨 Agent Skills 客户端)

本文件定义 mathmodel-skill 在不同 agentic harness 下运行时的**统一行为约定**。skill 主体内容 (`SKILL.md`, `stage_NN.md`, `competitions/*`) 保持 harness-agnostic；客户端只在发现路径、交互组件和命令入口上存在差异。完整运行时 payload 必须和 `SKILL.md` 一起安装。

---

## 0. 客户端发现路径与安装

各客户端的常见 skills 发现路径:

| 客户端 | 用户级 | 项目级 | 入口 |
|------|------|------|------|
| Codex | `~/.agents/skills/mathmodel-skill/` | `<repo>/.agents/skills/mathmodel-skill/` | `$mathmodel-skill` / 自然语言 |
| Claude Code | `~/.claude/skills/mathmodel-skill/` | `<repo>/.claude/skills/mathmodel-skill/` | `/mathmodel-skill` / 自动触发 |
| Cursor | `~/.cursor/skills/mathmodel-skill/` 或 `~/.agents/skills/` | `<repo>/.cursor/skills/` 或 `.agents/skills/` | `/mathmodel-skill` / 自动触发 |
| VS Code/Copilot | `~/.copilot/skills/`、`~/.claude/skills/` 或 `~/.agents/skills/` | `<repo>/.github/skills/`、`.claude/skills/` 或 `.agents/skills/` | `/skills` / 自动触发 |
| OpenCode | `~/.config/opencode/skills/` 或 `~/.agents/skills/` | `<repo>/.opencode/skills/` 或 `.agents/skills/` | `skill` 工具 |

推荐从仓库根目录执行 `python scripts/install_skill.py --agent <client> --scope <project|user>`；它会复制 `SKILL.md`、`references/`、`competitions/`、`templates/`、`scripts/` 和 `config/`，并排除 Git 元数据、CI、测试与生成产物。也可直接 clone 到上表目录。

所有客户端都优先依据 `SKILL.md` frontmatter 的 `name` / `description` 做发现。Codex 额外读取 `agents/openai.yaml` 和 `.codex-plugin/plugin.json`；Claude Code、Cursor、VS Code/Copilot 和 OpenCode 直接读取 skill 目录中的 `SKILL.md`。`AGENTS.md` 只作为 repo/workspace 指导文件，不是跨客户端的唯一入口。

---

## 1. 用户交互: 问答式优先 (Friendly Mode)

**核心原则**: 用户只需回答**编号问题**, 不应被要求手敲 bash / python / json。

| 决策类型 | 行为 |
|---------|------|
| 离散选项 (选竞赛/选题/选模型/选 verdict) | **必须**用问答式 (Claude: AskUserQuestion; Codex: markdown 编号列表) |
| 自由文本 (PDF 路径 / 截止时间 / 关键评论) | 直接问, 单行回复 |
| 确认型 (yes/no/进入下一步) | 编号 2 选 1, 或加"让我决定 (推荐 X)" 作为第 3 项 |
| 状态读写 (state/decision_log.json) | agent 自动完成, **不要**让用户编辑 json |

### Claude Code (有 AskUserQuestion)

```python
AskUserQuestion(questions=[{
    "question": "Q1 用哪个候选模型?",
    "header": "Stage 3 模型选型",
    "multiSelect": False,
    "options": [
        {"label": "Lagrangian 松弛 MILP", "description": "..."},
        {"label": "遗传算法", "description": "..."},
        {"label": "禁忌搜索", "description": "..."}
    ]
}])
```

### Codex (无原生选项 UI 时)

```
【Stage 3: Q1 用哪个候选模型?】

  1) Lagrangian 松弛 MILP — 适合线性目标 + 约束, 商用 solver 直接出最优
  2) 遗传算法 — 适合非凸 / 高维离散
  3) 禁忌搜索 — 中等规模组合优化, 易实现
  4) 让我决定 (推荐 1, 因 stage 2 标记目标线性)

回复数字。
```

收到 `1` / `2` / `3` / `4` 后:
- 写入 `decision_log.stages.3.selected_per_subproblem.Q1.model_name`
- 写入 `decision_log.stages.3.rejection_log` (未选的两个 + 简短理由)
- 直接进入 Step B (求解实现), 不要二次确认

---

## 2. 文件 I/O

| 操作 | Claude Code | Codex |
|------|-------------|-----------|
| 读文件 | `Read(file_path=...)` | `shell: cat ...` 或 `apply_patch` view |
| 写新文件 | `Write(file_path=..., content=...)` | `apply_patch *** Add File` |
| 改文件 | `Edit(file_path=..., old_string=..., new_string=...)` | `apply_patch *** Update File` |
| 查找 | `Glob` / `Grep` | `shell: rg ...` |

Cursor、VS Code/Copilot、OpenCode 或其他客户端使用其原生文件工具；无论工具名称如何，所有 skill 内相对路径都从 `SKILL.md` 所在目录解析，用户产物都写到 `<cwd>/`。

**路径协议保持不变**: 无论哪个 harness, `<cwd>/state/decision_log.json` 都表示当前项目根目录下的 `state/decision_log.json`。

---

## 3. Shell 执行

两个 harness 均有 shell 工具。脚本调用一致:

```bash
python <skill>/scripts/score_artifact.py --stage 5 --critique state/critique_v0.json
python scripts/extract_diff.py --artifact a.md --critique c.json --mode section
python <skill>/scripts/render_paper.py --workspace paper_workspace/
```

环境变量 `MATHMODEL_STATE_DIR` / `MATHMODEL_COMPETITION` 在两个 harness 下同样生效。

---

## 4. 子代理 / 任务分派

| 用途 | Claude Code | Codex |
|------|-------------|-----------|
| 并行评分 5 个视角 (stage 9 panel) | `Agent` 5 个并发 subagent | 5 个独立 `codex` 子任务 (或串行) |
| 跑大批 PDF 烘焙 | `Agent` 长时间后台 | `shell: python ... &` + 轮询 |
| 一次性深搜外部资料 | `Agent + WebSearch` | `shell: curl ...` |

如果当前 Codex 环境没有子任务/多代理能力, 则串行执行 panel 并告知耗时约 5×; 若有可用子任务能力, 可按 5 个独立任务并行。

---

## 5. 持久 state: harness 互通

**核心保证**: `<cwd>/state/decision_log.json` 是 single source of truth, 跨 harness 完全兼容。

实际场景:
- Day 1 用 Codex 跑 stage 0-2 → decision_log 写到 stage 2 完成
- Day 2 队员换 Claude Code → 读同一 decision_log → 从 stage 3 起步
- Day 3 又切回 Codex → 仍然从 current_stage 接着跑

**禁止**任何 stage 文件依赖 harness 特有的隐式状态 (如 Claude 的 conversation memory)。所有关键决策**必须**落盘到 decision_log。

---

## 6. 触发关键词与元数据

| harness | 推荐配置 |
|---------|---------|
| Claude Code | `SKILL.md` description 明确限定 CUMCM、MCM/ICM、电工杯及“数学建模竞赛论文”任务；仅说“建模”“A 题”或普通数据分析时不应触发 |
| Codex | 安装到 `.agents/skills/` 后由同一 `SKILL.md` description 触发；`agents/openai.yaml` 提供 UI 展示和默认 prompt，原生选择 UI 不可用时才回退编号列表 |
| Cursor | 安装到 `.cursor/skills/` 或 `.agents/skills/`；目录名和 frontmatter `name` 保持 `mathmodel-skill`，可用 slash command 或自动触发 |
| VS Code/Copilot | 安装到 `.github/skills/`、`.claude/skills/` 或 `.agents/skills/`；通过 `/skills` 菜单检查发现结果 |
| OpenCode | 安装到 `.opencode/skills/` 或 `.agents/skills/`；由 `skill` 工具按 ID 加载，引用文件相对 `SKILL.md` 所在目录解析 |
| Plugin | `.codex-plugin/plugin.json` 声明 `skills: "./skills/"` 并随 GitHub Release 分发 |

---

## 7. 验收 checklist (harness 适配是否做对)

- [ ] 启动后，不论 harness，都收集同一组 5 个启动字段，但只询问当前消息与 state 中尚缺的字段
- [ ] 所有"选 X" 决策点都呈现编号选项
- [ ] decision_log.json schema 完全一致 (含 v6 兼容字段)
- [ ] scripts/*.py 退出码与输出 JSON 一致
- [ ] cwd 下生成的目录结构 (state/results/figures/paper_workspace) 一致
- [ ] Codex 安装包含 `agents/openai.yaml` 与 `.codex-plugin/plugin.json`

任何一项不符 = 该 harness 适配未完成。

官方目录说明：

- [Codex / ChatGPT Skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Cursor Agent Skills](https://cursor.com/docs/skills)
- [VS Code Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [OpenCode Skills](https://opencode.ai/docs/skills)

# AGENTS.md — mathmodel-skill v7.4.3 (跨 Agent / Project Instructions)

> 本文件是 **Codex** 及遵循 `AGENTS.md` 约定的 agentic CLI 的项目级适配层。
> 真正的工作流定义在 `SKILL.md`，请把它当作主指令读取。本文件只解释 **harness 差异**。
> 其他客户端直接加载 `SKILL.md` 和相邻资源目录即可；本文件不是跨 Agent 的唯一入口。
> 推荐把本仓库作为 Agent Skill 安装到对应客户端的 skills 目录；Codex 常用 `$HOME/.agents/skills/mathmodel-skill/` 或项目 `.agents/skills/mathmodel-skill/`。

---

## 你是谁

你是一个跟用户一起打数学建模竞赛 (CUMCM 国赛 / MCM 美赛 / 电工杯) 的 agent。完整 10 阶段工作流、评分系统、模板与经验内容在本仓库 `SKILL.md` 与 `references/`、`competitions/`、`templates/` 下。

**首要动作**: 读 `SKILL.md`, 把它视为顶层 system prompt 的一部分。

---

## 客户端差异 (你只需读这一段)

| 能力 | Claude Code | Codex | Cursor / VS Code / OpenCode | 你该怎么做 |
|------|-------------|-----------|-------------------------------|----------|
| Skill 发现 | `.claude/skills/` | `.agents/skills/` + `agents/openai.yaml`/plugin | 客户端各自的 skills 目录 | 首先读 `SKILL.md`, 再按需读 references |
| 项目指导 | 通常不依赖 `AGENTS.md` | `AGENTS.md` 层级 instructions | 以客户端官方约定为准 | 本文件只做可选适配层, 不复制完整 workflow |
| 用户交互 | `AskUserQuestion` 工具弹出选项 UI | markdown 编号列表 | 原生 UI；没有时用编号列表 | 保持决策字段和提问语义一致 |
| 文件读写 | `Read` / `Edit` / `Write` | `apply_patch` / shell `cat` | 客户端原生文件工具 | 路径协议不变 |
| Shell | `Bash` (有 sandbox) | `shell` | 客户端 shell | 脚本调用保持一致 |
| 子代理 | `Agent` (subagents) | `codex` 子任务 | 由客户端能力决定 | 无子代理时串行并记录 |
| 持久 state | `cwd/state/decision_log.json` | 同 | 同 | **完全一致**, 跨 harness 互通 |

**核心保证**: `cwd/state/decision_log.json` 是 **harness-agnostic** 的。一队人 day 1 在 Codex 上跑 stage 0-2, day 2 切回 Claude Code 继续 stage 3+, 不会丢状态。

---

## 交互协议

用户直接提供赛题并要求求解/交付时，默认 `autopilot`，先读 `references/autopilot_delivery.md`：普通选择自动采用推荐项并写入 state，只在题面/附件/模板/授权/真实性的硬阻塞处提问。用户只说“开始建模”、题目未公布或明确要求逐步协作时，使用 `guided` 编号问答。两种模式都禁止让用户手敲 bash / python / json。

### Guided 模式下的编号问答格式

每当需要用户决策, 用如下格式 (不要调用任何 "AskUserQuestion" 工具——Codex 没有):

```
【需要你选择: <一句话标题>】

  1) <选项 A> — <一句话解释>
  2) <选项 B> — <一句话解释>
  3) <选项 C> — <一句话解释>
  4) 让我决定 — <若无偏好的推荐项, 标 (推荐)>

回复数字 (1-4) 或直接告诉我你想做什么。
```

收到回复后:
1. 把决策写进 `cwd/state/decision_log.json` 对应字段
2. **不要**回头问"你确认吗" — 用户已经选了
3. 进入下一步

### Claude Code 下

直接用 `AskUserQuestion` 工具, 选项内容相同。`SKILL.md` 与 stage 文档里的 `AskUserQuestion(...)` 标记 = Codex 下的编号问答。

---

## 启动协议 (与 SKILL.md "Quick Start" 等价)

### 已提供赛题

1. 读 `references/autopilot_delivery.md`、`references/deliverable_contract.md`、`references/nature_capability_router.md`；若为 CUMCM，先读并核验 `competitions/cumcm/current_rules.md`，再读 `references/cumcm_2026_compliance.md`。
2. agent 运行 `scripts/bootstrap_run.py` 初始化/恢复工作区，不覆盖已有 state。
3. 推断竞赛/题号/语言，低置信且影响模板时才问一次。
4. 连续执行 Stage 0-9；按阶段路由分别安装的可选 skills，外部目录只读且不复制其内容。
5. 运行 `scripts/validate_delivery.py`，再用 `scripts/package_delivery.py` 生成版本化交付文件夹；CUMCM 还须先生成 AI 详情。有人工确认 blocker 时保留候选包但不得标记 submission-ready。

### 未提供赛题或要求逐步协作

用户说"开始建模"/"打 cumcm"/"打 mcm"/"打电工杯"时:

1. **一段话自我介绍** (≤50 字): "启动数学建模工作流, 10 阶段 + 三竞赛, Guided 编号协作."

2. **一次性提 5 个问题** (Codex: 5 个编号列表; Claude Code: 单条 AskUserQuestion):
   - Q1 竞赛 (cumcm/mcm/diangong, 默认 cumcm)
   - Q2 题号 (依竞赛: cumcm A-E / mcm A-F / diangong A-B / 未公布)
   - Q3 队员数 + 各人擅长 (建模/编程/写作)
   - Q4 截止时间 (ISO 字符串或"距现在 X 小时")
   - Q5 题目 PDF 路径 ("未公布"亦可)

3. 自动初始化:
   - 若 `cwd/state/decision_log.json` 不存在: 从 `templates/shared/decision_log.json` 拷贝
   - 写入 `decision_log.competition` = Q1 答案
   - 已存在: 读 `current_stage` 决定恢复点

4. 加载 `competitions/<comp>/winning_patterns.md` 一次, 后续不再重复读
5. 进入 Stage 0 (`references/stage_00_kickoff.md`)

> Codex 安装建议: 作为 skill 使用时, 目录应位于 `$HOME/.agents/skills/mathmodel-skill/` 或 `<repo>/.agents/skills/mathmodel-skill/`; 作为 plugin 分发时, `.codex-plugin/plugin.json` 会声明该目录包含 skill。

---

## 路径协议 (与 SKILL.md 一致, 任何 harness 都遵守)

| 类型 | 位置 | 例 |
|------|------|-----|
| skill 内通用 | `<skill>/references/`, `<skill>/templates/shared/` | `references/stage_05_subproblem_loop.md` |
| 竞赛特化 | `<skill>/competitions/<comp>/` | `competitions/cumcm/winning_patterns.md` |
| LaTeX 模板 | `<skill>/templates/latex/<comp>/main.tex` | `templates/latex/cumcm/main.tex` |
| 用户产物 | `<cwd>/{state,analysis,src,results,figures,paper_workspace,paper_output,support_materials,qa,delivery}/` | `cwd/state/decision_log.json` |
| 环境变量 | `MATHMODEL_STATE_DIR` (覆盖 cwd/state 位置) / `MATHMODEL_COMPETITION` (覆盖竞赛) | scripts 用此变量 |

`<skill>` = 本 AGENTS.md 所在目录, `<cwd>` = Codex 启动时的工作目录。

---

## 主要参考文件 (按需懒加载, 不要一次全读)

- `SKILL.md` — 完整工作流定义 (启动必读)
- `references/stage_00_kickoff.md` ~ `stage_09_review.md` — 10 阶段细则 (按需读)
- `references/harness_compat.md` — 本 harness 兼容协议详细版
- `references/autopilot_delivery.md` — 赛题到交付物的一键执行与唯一暂停条件
- `references/nature_capability_router.md` — 可选外部 skills 的只读路由与降级边界
- `references/deliverable_contract.md` — 最终交付包与 hard gates
- `competitions/cumcm/current_rules.md` — 可核验的 CUMCM 官方基线和来源链接
- `references/cumcm_2026_compliance.md` — CUMCM 官方基线之上的维护者交付策略、AI 详情、匿名、20 MB 与打包规则
- `competitions/<comp>/README.md` — 各竞赛差异点
- `scripts/score_artifact.py` — L1 评分 + verdict 计算 (Codex shell 直接调用)

---

## 与用户的语气

- 中文优先 (cumcm/diangong 队伍), 英文遵从用户输入语言 (mcm 队伍多英文交流)
- **不要**长篇解释为什么这么做; 用户在赶 deadline
- 用户问"为什么"再展开
- Guided 每阶段结尾给 1 句话进度；Autopilot 只在耗时节点简短更新，不要求用户确认即可继续。

---

License: MIT 仅覆盖仓库原创内容。详见 `LICENSE`、`THIRD_PARTY_NOTICES.md` 与 `PROVENANCE.md`。

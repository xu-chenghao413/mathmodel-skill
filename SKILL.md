---
name: mathmodel-skill
description: "输入 CUMCM、MCM/ICM 或电工杯赛题后，自动完成题面解析、建模、真实代码求解、统计与稳健性、科研制图、引用核验、竞赛论文/PDF、互盲终审和可复现交付包；也支持逐阶段 Guided 协作。Use for 建模、数模、竞赛论文、模型选择、灵敏度分析、摘要/终稿审核，或用户要求从赛题一键输出交付物。Do not use for ordinary academic papers unrelated to modeling contests."
---

# mathmodel-skill — 数学建模三竞赛通用 Skill (v7.3.4)

10 阶段把"3-4 天打 1 篇竞赛论文"工程化。用户直接给出赛题时默认 **Autopilot 一键交付**：自动完成读题、建模、代码求解、统计/制图、引用、论文、PDF 视觉 QA 与交付清单；只说“开始建模”时保留编号问答式 Guided Mode。每阶段产出经过 rubric 自评、section-level patch、跨阶段回检与终局互盲评审。

**v7.2 更新**: 在 v7.1 合规与单文件夹交付基础上，加入自适应 `page_budget.json`；正文按任务重要性和证据负担分配，附录按完整复现自然分页。新增 `novelty_ledger`、算法名称—数学定义—代码—求解器日志—实验结果一致性硬门，以及只保留关键实质交互的 AI 披露。可选外部 skills 不是硬依赖。

**v7.3 更新**: 已有论文按最小补丁修订，先锁定原稿章节、正文页数、图表编号/数量/尺寸和完整附录，再逐项修复可核实问题。公开发行版移除未授权第三方模板、用户案例和逐页私有数据，保留独立编写的工作流、聚合统计、证据追溯和数值稳定性检查。

## 已有论文修订：先保全基线

“审计后修改”不等于重写。必读 `references/manuscript_revision_contract.md`：保留用户已认可的结构、图表和篇幅；每处改动对应一个已核实问题。未获授权不得换主模型、全篇压缩、删图迁表、缩图或重做全部附录。修订后以最新 PDF 实测页数，并比对源稿的章节、图表清单和尺寸；未完成的科学问题如实留在审计清单，不得为宣称全部解决而替换成未经验证的新答案。

---

## Codex V7 原生入口

Codex 优先按 skill 目录发现本文件:

- 用户级安装: `$HOME/.agents/skills/mathmodel-skill/`
- 项目级安装: `<repo>/.agents/skills/mathmodel-skill/`
- UI 元数据: `agents/openai.yaml`
- 插件分发元数据: `.codex-plugin/plugin.json` + `skills/mathmodel-skill/SKILL.md` shim
- 项目指导: `AGENTS.md` 仍可作为 repo / workspace 级 instructions, 但不是唯一入口

当 skill 已安装后, 用户可直接说"开始建模"或显式说"使用 `$mathmodel-skill` 开始建模"。

---

## Harness 兼容 (Claude Code / Codex)

本 skill v7.3.4 以 Codex Skills 为一等入口, 同时保持 harness-agnostic 设计:

| harness | 入口文件 | 用户交互工具 | 状态文件 |
|---------|---------|-------------|---------|
| Claude Code | `SKILL.md` (本文件) | `AskUserQuestion` 工具 | `cwd/state/decision_log.json` |
| Codex CLI / Codex app | skill 目录中的 `SKILL.md` + 可选 `AGENTS.md` | markdown 编号列表 | 同上 (**互通**) |

跨 harness 互通: day 1 用 Codex 跑 stage 0-2, day 2 切回 Claude Code 接着 stage 3+, 状态完全保留。详见 `references/harness_compat.md`。

---

## 两种交互模式

`interaction_mode` 与 `fast / standard / championship` 正交：前者决定是否暂停问用户，后者决定分析深度。

| interaction_mode | 触发 | 行为 |
|---|---|---|
| `autopilot` | 用户已提供赛题文本/PDF/图片/附件并要求求解或交付 | 从 Stage 0 连续跑到可验证交付包；普通决策自动采用推荐项并记录；仅硬阻塞提问 |
| `guided` | 用户只说“开始建模”、题目未公布，或明确要逐步协作 | 关键决策使用编号问答 |

Autopilot 必读 `references/autopilot_delivery.md` 与 `references/deliverable_contract.md`。涉及文献、统计、图、论文、引用或终审时按 `references/nature_capability_router.md` 路由；绝不修改 Nature skills。

## Guided 问答协议 (Friendly Mode)

**核心原则**: Guided 用户只需回答**编号问题**, 不应被要求手敲 bash / python / json。Autopilot 中这些问题由 agent 采用推荐项并写入 state，不暂停。

- Guided 的离散选项 (选竞赛 / 选题 / 选模型 / verdict 决策) → **必须**用问答式
- 自由文本 (PDF 路径 / 截止时间) → 单行回复
- 状态读写 (decision_log.json) → agent 自动完成
- 每个 stage 的关键决策点都有 "让我决定 (推荐 X)" 兜底选项, 用户无脑选 4 也能跑通

Claude Code: 用 `AskUserQuestion` 工具; Codex: 用 markdown 编号列表 (1-4 + 兜底)。两者语义等价, 见 `references/harness_compat.md` §1。

---

## 路径解析协议 (任何阶段必读)

| 类型 | 位置 | 例 |
|------|------|-----|
| skill 内通用 | skill 根目录的相对路径 | `references/stage_05_subproblem_loop.md`, `templates/shared/decision_log.json` |
| **竞赛特化** | `competitions/<comp>/...` 按 decision_log.competition dispatch | `competitions/cumcm/winning_patterns.md`, `competitions/mcm/abstract_template.md` |
| **LaTeX 模板** | `templates/latex/<comp>/main.tex` | `templates/latex/cumcm/main.tex`, `templates/latex/mcm/main.tex` |
| 用户产物 | 用户 `cwd/` 相对路径 | `cwd/{state,analysis,src,results,figures,paper_workspace,paper_output,support_materials,qa,delivery}/` |
| state 持久化 | `cwd/state/decision_log.json` | 各 stage 必读必写 |
| 环境变量 | `MATHMODEL_STATE_DIR` (兼容 `CUMCM_STATE_DIR`) / `MATHMODEL_COMPETITION` 可覆盖 | scripts 用此变量 |

约定: `<skill>/` = skill 安装目录, `<cwd>/` = 用户 cwd, `<comp>/` = 当前竞赛 (cumcm | mcm | diangong)。

---

## Quick Start

### A. 用户直接提供赛题 → 默认一键交付

```text
1. 判断 source packet 是否包含可读赛题与必要附件。
2. 读取 references/autopilot_delivery.md、deliverable_contract.md、nature_capability_router.md；若为 CUMCM，先核验 `competitions/cumcm/current_rules.md`，再读 `references/cumcm_2026_compliance.md`。
3. 自动运行 scripts/bootstrap_run.py 初始化或恢复 state；不要覆盖已有文件。
4. 从题面/文件名推断 competition、year、letter、language；低置信且会影响模板时才问 1 个问题。
5. 加载 competitions/<comp>/winning_patterns.md 与当前 stage 文档，连续执行 Stage 0-9；CUMCM 在写正文前运行 `scripts/plan_paper_budget.py`，先锁定正文/附录计数口径和按证据量分配的小问篇幅。
6. 先以 scripts/validate_delivery.py exit code 0 作为核心机械门；科学/视觉 blocking concern 仍由 Stage 9 判断。
7. 所有竞赛最后运行 `scripts/package_delivery.py` 输出版本化文件夹；CUMCM 须先生成 `AI 工具使用详情.pdf`，有人工确认 blocker 时保留候选包和 `NOT_SUBMISSION_READY.md`。
```

### B. 用户只说“开始建模” → Guided

```
1. 一段话介绍 (≤50 字): "启动数学建模工作流, 10 阶段 + 三竞赛, Guided 编号协作."

2. 一次性 5 问 (Claude Code: AskUserQuestion 单条消息; Codex: 5 个编号列表):
   - 竞赛 (cumcm 国赛 / mcm 美赛 / diangong 电工杯, 默认 cumcm)
   - 题号 (依竞赛: cumcm A-E / mcm A-F / diangong A-B; "未公布"亦可)
   - 队员数 + 各人擅长 (建模/编程/写作)
   - 截止时间 (ISO 字符串或 "距现在 X 小时")
   - 题目 PDF 路径 ("未公布"亦可)

3. 自动初始化 (agent 运行 `scripts/bootstrap_run.py --mode guided`; 不要让用户编辑 json):
   - 不存在 state → 从 v4 模板初始化
   - 已存在 → `--resume` 并读 current_stage 决定恢复点

4. 加载 competitions/<comp>/winning_patterns.md 一次 (建立基线), 后续不再读

5. 进入 Stage 0 (references/stage_00_kickoff.md), 不重复问已问过的问题
```

**已有 state 触发** (用户中途回到 skill):
```
1. 读 cwd/state/decision_log.json 的 competition 与 current_stage
2. 加载对应 stage_NN.md (按需结合 competitions/<comp>/* 内容)
3. 不重复读 winning_patterns
```

---

## 三竞赛 × 三模式 矩阵

时长 / 语言 / 模板 / 数据状态由 competition 决定；token 预算 / 反馈深度由 mode 决定；暂停策略由 interaction_mode 决定。三者**正交组合**。

| Competition | 时长 | 语言 | LaTeX | 子问数 IQR | 数据状态 |
|---|---|---|---|---|---|
| cumcm | 72h | 中文 | xelatex / 原创 ctexart | [3, 5] | 91 份来源文档的聚合统计，59 份成功提取 |
| mcm | 96h | English | pdflatex / article | [3, 6] | seed v0.1 |
| diangong | 72h | 中文 | xelatex / ctex | [6, 8] | seed v0.1 |

| Mode | Token | 反馈层 | 用途 |
|---|---|---|---|
| fast | ≤ 50k | L1 单次 + 终局硬门/压缩终审 | 选题试跑；若要求交付仍保留复现/统计/PDF/终审门 |
| standard | ≤ 200k | L1+L2+终局 L3 | 默认主流程 |
| championship | ≤ 500k | L1+L2+L3+L4 + red-team | 提交前最后冲刺 |

模式自动推荐 (按距 deadline 剩余):
- > 60h: standard (最后 6h 升 championship)
- 24-60h: standard
- 6-24h: fast 关键阶段 + championship 终审
- < 6h: 直接进 stage 9 (championship)

---

## 10 阶段索引

| # | 阶段 | reference | 时长 | 反馈 | 竞赛差异点 |
|---|------|-----------|------|------|-----------|
| 0 | source packet + 团队/环境启动 | `stage_00_kickoff.md` | 1h | L1 | 时长 / 语言 / 编译器 / 题号体系 |
| 1 | 选题 (多题对比 → 1) | `stage_01_problem_selection.md` | 2-4h | L1 | 题号体系 (A-E/A-F/A-B) + task_type 写入 |
| 2 | 问题深度解析与分解 | `stage_02_analysis.md` | 2-3h | L1 | 通用 |
| 3 | 模型选型 (≥3 候选) | `stage_03_model_selection.md` | 2-4h | L1 + 反事实 | 通用 |
| 4 | Foundation (假设+符号+术语) | `stage_04_foundation.md` | 1h | L1 | 通用 |
| 5 | **递归子问题循环** Q1..Qn + 真实运行 + per-Qi 聚合 | `stage_05_subproblem_loop.md` | 6-12h × n | L1 + 子检查点 | 子问数差异; 复现与数据泄漏检查 |
| 6 | 统计验证 + 全局灵敏度 / 稳健性 | `stage_06_robustness.md` | 2-3h | L1 + L2 | 工程参数 vs 数学参数; 区间与失效边界 |
| 7 | 模型评价 + 推广 | `stage_07_evaluation.md` | 1-2h | L1 | 通用 |
| 8 | 证据化论文写作 + 引用核验 | `stage_08_writing.md` | 12-30h | L1 | 自适应页预算 + 摘要/LaTeX + 术语/数值一致性；CUMCM 2026 AI 声明/附录 |
| 9 | 互盲终审 + PDF 视觉 QA + 交付打包 | `stage_09_review.md` | 2-6h | L1 + L3 | 3 份互盲报告 + synthesis + manifest + 版本化交付文件夹 |

---

## 加载协议 (节省 token 的关键)

**只在进入阶段 N 时加载** `references/stage_NN_*.md`。**切勿**一次性全读。

- Autopilot 启动: 额外加载 `references/autopilot_delivery.md` 与 `references/deliverable_contract.md`
- competition 为 `cumcm`: Stage 0、8、9 先核验 `competitions/cumcm/current_rules.md`，再加载 `references/cumcm_2026_compliance.md`；当前赛年新通知优先并记录覆盖关系
- 需要 Nature 能力: 加载 `references/nature_capability_router.md`, 然后只读被路由 skill 的完整 `SKILL.md` 及其本次所需 fragments

各阶段额外加载 (按需 + 按 competition 切换):
- 每阶段开头: `cwd/state/decision_log.json` 必读
- 每阶段结尾: `cwd/state/decision_log.json` 必写 (核心决策 + 5 维评分)
- stage 1-9: `references/rubrics.md` 对应章节 (L1 评分用)
- **stage 1**: `competitions/<comp>/topic_specs.json` (题号 → task_type 映射)
- stage 3, 5: `references/model_catalog.md` (跨竞赛通用)
- **stage 5**: per-Qi 评分跑完后调 `scripts/score_artifact.py --mode aggregate_qi` 聚合
- **stage 5-6**: 统计/图表路由 + `qa/reproducibility.json`, `qa/statistics_audit.md`
- **stage 8**: `competitions/<comp>/{winning_patterns, phrase_bank, abstract_template, paper_skeleton}.md` + 写作/润色/引用路由；CUMCM 生成 `analysis/page_budget.json`、`analysis/novelty_ledger.json`、算法一致性审计、AI 声明和关键事件级详情 PDF
- **stage 8 硬阈值评分**: `competitions/<comp>/empirical.json` 注入 evidence (cumcm 真值; mcm/diangong seed 自动带 [seed: ...] 标记)
- **stage 9**: `competitions/<comp>/anti_patterns.md` + `rubric_overlay.json` + `feedback_layer3_panel.md` + PDF/交付合同；CUMCM 最后执行版本化交付打包
- **stage 9 已有论文修订**：优先执行 `references/manuscript_revision_contract.md`；公开 skill 不内置用户稿件、评分或历史迭代案例。
- **stage 9 数值与推断检查**：关键结果用不同实现或可观测量交叉核验，差异先调查假设、单位、色散、预处理和优化；不得直接把替代算法当真值。普通 F 检验须满足嵌套及误差分布条件；AIC 不要求嵌套，但要求同一数据上的可比似然与正确参数计数。相关光谱数据需验证相关误差模型或合适的分块验证，所有数据依赖步骤须在训练折内完成。病态基函数检查尺度、条件数及环境敏感性，不能仅凭版本差异断言根因。`p5/p95` 为中央 90% 区间；先验传播、场景范围和抽样置信区间必须分名。
- 触发反馈时: 对应 `references/feedback_layer*.md`
- harness 适配差异 (Codex 用户必读): `references/harness_compat.md`

---

## 收敛准则 (统一定义, 三处一致)

**verdict 优先级 (从高到低)**:

| verdict | 触发 | 行为 |
|---------|------|------|
| `block` | issues 含 ≥1 high-severity | Guided 暂停；Autopilot 先最小修复，仅命中 hard blocker 才问用户 |
| `pass_early` | raw_min ≥ 9 AND weighted_mean ≥ 9 | iter-1 早退 |
| `pass` | raw_min ≥ 7 AND weighted_mean ≥ 8 | 进下一阶段 |
| `pass_with_review` *(stage 5)* | 任 Qi mark_for_review 但加权阈值满足 | 进 stage 6, L2 必读 review_qis |
| `refine` | 其他 | section-patch 精修, iter+=1 (cap 3) |
| `refine_partial` *(stage 5)* | 任 Qi.min < 7, 其他 Qi 已 pass | 仅 refine 该 Qi, 不动其他 |
| `carryover` | iter == 3 仍 refine | 进下一阶段, 标记由 L2 处理 |

`weighted_mean` = Σ(s_i × w_i) / Σ(w_i), 权重来自 `config/dim_weights.json[<comp>][<task_type>]` (clamp [0.7, 1.5]); `task_type=default` 全 1.0 等价老逻辑。

此定义在 `feedback_layer1_critic.md` / `rubrics.md` / `scripts/score_artifact.py` 三处必须**完全一致**。

---

## 状态持久化

每阶段:
- 开头: `Read cwd/state/decision_log.json`, 核对 current_stage 与上下文
- 结尾: 更新 stage 节点 (核心决策 + 摒弃方案 + 评分), `current_stage += 1`

`decision_log.json` v4.1 schema 关键字段 (与 `templates/shared/decision_log.json` 对齐):
- root: `competition`, `task_type`, `mode`, `current_stage`, `budget`, `events`
- execution: `interaction_mode`, `status`, `source_packet`, `nature_router`, `checkpoints`, `blockers`
- stage_5 扩展: `qi_count`, `qi_weights`, `qi_status`
- scores 扩展: 含 `weighted_mean`, `review_qis`, `refine_qis` (stage 5 加权聚合用)
- evidence / artifacts / qa: 只存摘要、locator、产物路径和校验状态
- compliance.cumcm: 2026 规则集、AI 使用与人工确认、摘要/官方正文/附录分开计数、页边距/匿名审查、最终交付包路径；人工确认字段不得由 agent 自行置 true
- stage 8: `page_budget` 保存计划与实际页数、动态小问权重和异常说明；`novelty_ledger` 保存创新类型及证据；`qa/algorithm_claim_consistency.json` 必须零 blocking 才可提交

L2 跨阶段回检 (stage 5/6/8 末尾) 读这个文件主动找冲突, 触发**定向回滚**: 不重做整阶段, 只针对冲突点。

---

## Token 预算纪律

- L1 Critic 强制 JSON 输出, ~500 token/次
- 精修策略: section-level patch (`scripts/extract_diff.py`), 不重传完整 artifact (省 ~60% token)
- references/ 与 competitions/ 文件**懒加载**, 本 SKILL.md 主体 ≤ 6k tokens
- 阶段完成后, artifact 摘要 + 关键数据 + 路径写入 decision_log, 不在上下文保留全文
- 超预算 30% → 自动降级 (championship → standard, standard → fast)

---

## 用户指令快捷

- "进入 stage N" / "重做 stage N" → 跳转
- "切到 mcm" / "切到 cumcm" / "切到 diangong" → 改 decision_log.competition (注意已有 state 兼容性)
- "升级到 championship" → 启用 L3 + L4 + red-team
- "切到 fast" → 关闭迭代
- "回退到 stage M" → 读 decision_log, 回退 current_stage 并清理 ≥M 节点
- "做 L2 回检" → 立即触发 cross-stage backtrack
- "看进度" → 输出 decision_log 摘要 + 当前评分

---

## 数据来源声明

- `competitions/cumcm/`: 91 份 2023–2025 来源文档的聚合测量，其中 59 份成功文本提取并进入 `empirical.json`；只发布统计字段和独立撰写的通用规则，不发布 PDF、提取文本或用户逐页案例。这些观察是经验先验，不是官方规则
- `competitions/mcm/`: SEED v0.1, 基于 COMAP 公开 scoring rubric + Outstanding Winner 公开模式手写; empirical 占位
- `competitions/diangong/`: SEED v0.1, 基于历年题量 + 公开评审标准估算; empirical 占位
- 通用模型清单 `references/model_catalog.md` 跨竞赛复用

后续如取得新的、明确允许处理的来源文档（例如公开许可或资料所有者书面授权），可用 `scripts/ingest_papers.py --competition <comp>` 在仓库外重新烘焙覆盖 seed；不得把原始文档或提取文本带回公开仓库。

---

## 与外部资源及可选 skills 的关系

核心建模与交付合同自包含；联网检索和分别安装的外部 skills 是按需增强，不可用时必须降级并记录。不得因为外部能力缺失而伪造引用或结果。CUMCM 先核验官方基线，再执行 `cumcm_2026_compliance.md` 中明确标注的维护者策略，并用 `package_delivery.py` 生成一个文件夹。

可用的 `nature-*` skills 通过 `references/nature_capability_router.md` 只读路由。不得复制、修改或再分发其源码、文档和资产；它们不是本项目依赖，也不表示任何官方关联。主链可选使用 academic-search、statistics、figure、writing、polishing、ref-verifier、reviewer；reader、paper-card、downloader、citation、data、paper2ppt 条件触发。以下资源也可作人工补充:
- 国赛: `personqianduixue/Math_Model`, `datawhalechina/intro-mathmodel`, `dxs.moe.gov.cn` 优秀论文展廊
- 美赛: COMAP 官网 `comap.com`, `MCM Tutorial` (Frank Giordano)
- 电工杯: 中国电机工程学会论文集

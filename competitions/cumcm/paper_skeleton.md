# 国赛论文骨架（CUMCM 2026 电子版）

> 电子版不含承诺书/编号页，第一页必须是摘要，不要目录。官方正文从摘要后一页计到附录前（含 AI 声明与参考文献）。本项目默认执行 26–28 页维护者策略；官方规则仍以 `current_rules.md` 为准。附录单独计数且以完整复现自然结束。
> **详细写作流程、prompt、自检清单见 `references/stage_08_writing.md`**, 本文件不重复。

---

## 自适应页数监控

写作前运行 `scripts/plan_paper_budget.py`，把结果写入 `analysis/page_budget.json`。表中不得预填固定页数：

| 账本 | 计数规则 | 门/目标 |
|---|---|---|
| 摘要 | PDF 第 1 页 | 原则上 1 页 |
| 官方正文 | 摘要后一页至附录前，含 AI 声明与参考文献 | 本项目默认策略 26–28；compact/balanced/dense 仅为初始化锚点 |
| 前置内容 | 重述、路线、必要假设和符号 | 最短充分，不得挤压结果 |
| 核心小问 | 按重要性/场景/推导/创新证据/验证/复用动态分配 | 不平均；异常份额须说明 |
| 验证与评价 | 可分问完成或独立成节 | 不重复已有证据 |
| 附录 | 附录首页至 PDF 末页（必须有"附录"大标题 + "附录A/B/C"前缀） | 不设页数目标；完整性驱动；见下方附录 LaTeX 模板 |

聚合观察见 `empirical.json` 与 `empirical_notes.md`；它们均非官方规则。

---

## 骨架 (markdown 中间产物 → render_paper.py → 本项目原创 ctexart LaTeX)

```
[电子版第一页：论文标题 + 一页逐问证据闭环摘要；页脚中部从 1 编号]
关键词: <填与题目对象、核心方法和决策任务相关的关键词；数量按当前模板>

# 1. 问题重述

## 1.1 问题背景
<填: 最短充分的领域背景 + 本题场景>

## 1.2 问题描述
<填: 自己语言重述三个子问题, 不抄题>

# 2. 问题分析

## 2.1 问题一分析  <填: 类型+约束+决策变量+目标+难点+策略>
[图 1: 问题一求解流程图]
## 2.2 问题二分析  <同>
## 2.3 问题三分析  <同, 引用 Q1/Q2 结果>

# 3. 模型假设
<填: 只保留实际求解所必需的假设；每条给支撑（文献/数据/物理意义）及可能造成的偏差，见 assumption_table.md>

# 4. 符号说明
<填: 覆盖全文核心符号并给单位/类型; 见 notation_table.md>

# 5. 模型的建立、求解、结果与验证（主体，按 page_budget 动态分配）

## 5.1 问题一: <与数学定义、代码和 solver log 一致的名称>
### 5.1.1 模型建立  <填: 决策变量 + 目标函数 + 约束>
### 5.1.2 求解算法  <填: 步骤 + 流程图>
### 5.1.3 求解结果与分析  <填: 数值结果 + 图 + 物理意义>

## 5.2 问题二: <同；真实复用时给上游 locator>
## 5.3 问题三: <同；无依赖时不强造复用链>

# 6. 灵敏度分析与稳健性检验
<填: 选择与模型风险匹配的验证/灵敏度；不强制 LHS/Sobol; 见 sensitivity_table.md>

# 7. 模型评价与推广
## 7.1 优点  <填: 仅列与本题结果相关且有证据的优点>
## 7.2 局限与改进  <填: 说明具体失效条件、可行替代方案及代价；不凑条目>
## 7.3 改进方向
## 7.4 推广

# AI 工具使用声明
本参赛队在竞赛过程中使用了 AI 工具，主要用于【与 qa/ai_usage_log.json 一致的真实简要用途】，详细使用情况见支撑材料。

# 参考文献
<填: 覆盖正文全部实际引用，按当前模板规范排版；不为凑数量加入无关条目>

# 附录 A: 支撑材料文件列表
<填: 与最终支撑材料.zip 完全一致的文件清单>

# 附录 B: 建模完整源程序
<填: 与实际运行同源、服务于建模与结果生成的所有 Qi 求解、数据处理、绘图与灵敏度代码；含 Excel/SPSS 交互命令；中文注释并标明对应论文位置；不得截断。注意：仅列入建模与结果生成链路，纯复现/交付/文档工具（如 compile_paper、package_delivery、validate_delivery、build_ai_disclosure、run_all、run_chain）不纳入代码清单>

# 附录 C: 计算结果详表
```

**附录 LaTeX 模板（强制结构）**：

```latex
\clearpage
\appendix

% 附录大标题（居中，与一级节标题同视觉层级）
\begin{center}
{\zihao{3}\heiti 附录}
\end{center}
\vspace{0.5em}

% 节显示为"附录A/附录B/附录C"，子节为"A.1"式
\renewcommand{\thesection}{附录\Alph{section}}
\renewcommand{\thesubsection}{\Alph{section}.\arabic{subsection}}

\section{支撑材料文件列表}
...
\section{建模完整源程序代码}
...
\section{计算结果详表}
...
```

- `\clearpage` 强制附录新起一页，确保页数三账闭合
- 若 cls 已 `\usepackage[title]{appendix}` 但未生效（自定义类常见），使用上方手动方案可控
- validate_delivery.py 检查 paper.tex 必须同时包含：① `\renewcommand{\thesection}{附录\Alph{section}}`；② `\heiti 附录` 或同义大标题；缺一即阻断项

---

## 与其他模板的关系

| 章节 | 对应模板 |
|------|--------|
| 摘要 | `abstract_template.md`（一页逐问证据闭环） |
| §3 假设 | `assumption_table.md` |
| §4 符号 | `notation_table.md` |
| §6 灵敏度 | `sensitivity_table.md` |
| 全文写作流程 | `references/stage_08_writing.md` |
| 写作观察 | `competitions/cumcm/winning_patterns.md`（独立撰写，不是获奖承诺） |
| 句式 | `references/phrase_bank.md` |
| 反模式自检 | `competitions/cumcm/anti_patterns.md` |
| 2026 格式/AI/交付 | `references/cumcm_2026_compliance.md` |

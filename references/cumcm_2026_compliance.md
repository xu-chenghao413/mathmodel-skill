# CUMCM 2026 格式、AI 与交付检查

仅在 `decision_log.competition == "cumcm"` 时加载。这里是本项目的执行合同；当届组委会正式文件、赛题包和赛区通知始终优先。

## 1. 规则层级与来源

1. 先读取并核验 `competitions/cumcm/current_rules.md` 中的官方链接。
2. 官方文件决定参赛资格、文件格式、页数、匿名和 AI 披露要求。
3. 本文件的“维护者策略”是为了让交付更容易审查而设置的更严格门槛，不能冒充官方规则；若与当届正式文件冲突，应记录冲突并服从官方文件或用户明确要求。

## 2. 官方基线摘要

当前仓库记录的官方基线包括：

- 电子论文不含承诺书和编号页，第一页为摘要页；
- 电子论文不超过 20 MB，正文不超过 30 页，附录另计；
- A4 版式、四边至少 2.5 cm，不设置全国统一字号/行距；
- 不得包含队员、学校、赛区等身份信息；
- 支撑材料是单独的 ZIP/RAR 文件，不超过 20 MB；
- 使用 AI 时按当届规则做真实声明、工具信息、用途和人工核验记录。

上述内容是摘要，不替代正式通知。来源和验证日期见 `competitions/cumcm/current_rules.md`。

## 3. 本项目的维护者策略（有意更严格）

以下门槛是本 skill 为了形成稳定、可复核交付而采用的策略：

- 摘要（含标题和关键词）恰好 1 页；
- 电子论文官方正文控制在 26–28 页；
- 附录按“支撑材料文件列表 → 完整源程序代码 → 计算结果详表”三段组织；
- 有图意图的流程图使用真实图形（TikZ、PNG、SVG 或 PDF），不使用文字加箭头伪造；
- 分组箱线图标出适用的样本量 `n=`，并在图注中解释支撑结论所需的读图要素；
- 参考文献默认要求 `year >= 2000` 且逐条核验；若基础理论必须保留经典旧文献，需在审计记录中说明理由；
- 任何一项硬门失败都将交付状态标为 `blocked`，但 README 和报告必须称其为维护者策略而非官方规定。

## 4. 页数状态口径

`decision_log.compliance.cumcm.paper` 同时保存：

- `pdf_total_pages`：电子 PDF 全部物理页；
- `abstract_pages`：摘要页数；
- `official_body_start_pdf_page`、`official_body_end_pdf_page`：正文起止页；
- `official_body_pages = end - start + 1`：维护者策略检查字段，须满足 `26 <= official_body_pages <= 28`；
- `appendix_start_pdf_page`、`appendix_pages`：附录起始页和附录页数；
- `pdf_total_pages = abstract_pages + official_body_pages + appendix_pages`：电子版三账恒等式。

不得用“摘要至参考文献共 X 页”或“叙述正文 X 页”替代上述字段。论文样本只能作为排版观察，不能覆盖官方规则或用户明确要求。

## 5. 电子论文与附录检查

- 第一页是摘要；不含目录、承诺书或编号专用页；
- AI 声明位于参考文献之前；未使用 AI 时才可使用无 AI 声明；
- 附录包含支撑材料文件列表、实际使用的完整源程序、必要的交互命令和结果详表；
- 附录标题、编号、源文件和支撑材料清单一一对应；
- PDF 可选择文本，无身份信息、裁切、乱码或明显超出版心；
- 论文中的文件名、PDF metadata、支撑材料和压缩包同样执行匿名检查。

推荐的 LaTeX 结构为：

```latex
\clearpage
\appendix
\begin{center}
{\zihao{3}\heiti 附录}
\end{center}
\renewcommand{\thesection}{附录\Alph{section}}
\section{支撑材料文件列表}
\section{完整源程序代码}
\section{计算结果详表}
```

## 6. AI 使用详情

调用本 skill 生成或修改赛题解答时，按当届规则真实披露 AI 使用，不得把工具调用伪装成“未使用 AI”。`AI 工具使用详情.pdf` 至少记录：

1. 实际模型名称和版本；
2. 使用目的与阶段；
3. 主要提示方式和过程摘要；
4. 采纳内容、人工修改和人工核验；
5. 对受影响代码、图表、章节或结论的影响。

本项目默认只记录“关键实质事件级”摘要，不转录完整聊天。不能以“只记关键交互”为理由漏报影响模型、数据、代码、结果或结论的采用过程。

确认字段（如 `team_led_core_modeling_confirmed`）必须由参赛队明确填写，agent 不得自行设为 `true`。

## 7. 运行与打包顺序

```text
修改 .tex / 源数据
→ 同步实际编译目录
→ 完整编译并渲染检查
→ 写入 page_structure_audit.json
→ 运行 validate_delivery.py
→ 运行 package_delivery.py
```

支撑材料包根目录直接放 `AI 工具使用详情.pdf`，不把它作为最终交付物藏在 `qa/` 中。没有真实运行、缺少附件或人工确认未完成时，必须保留 `NOT_SUBMISSION_READY.md` 或等价 blocker。


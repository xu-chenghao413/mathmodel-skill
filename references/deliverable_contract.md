# 数学建模最终交付合同

所有路径相对用户工作区 `<cwd>`。允许已有项目采用等价文件名，但必须在 `DELIVERY_MANIFEST.md` 映射到下列逻辑角色。

## 1. 工作区布局

```text
input/                    赛题与附件的只读索引/哈希，不改原件
data_raw/                 用户允许复制时保存原始数据；否则记录外部绝对路径
data_processed/           可重建的清洗数据与 schema
analysis/                 要求矩阵、模型选择、假设/符号/术语 ledger
src/                      可复跑的主代码与入口
results/                  机器可读结果、表格、日志
figures/                  图与绘图源代码
paper_workspace/          分节 Markdown、LaTeX、BibTeX 中间文件
paper_output/             最终 paper.tex / references.bib / paper.pdf
support_materials/        需放入竞赛支撑材料的外部数据、补充说明等显式暂存区
qa/                       统计、引用、图表、复现、评审、PDF 与交付校验
state/decision_log.json   跨阶段状态
delivery/                 不覆盖旧版的最终交付文件夹
DELIVERY_MANIFEST.md      用户入口
```

## 2. 必交付物

| 逻辑角色 | 首选路径 | 最低要求 |
|---|---|---|
| 最终论文 | `paper_output/paper.pdf` | 可打开、模板正确、无裁切/乱码/占位符 |
| 可编辑论文源 | `paper_output/paper.tex` | 与 PDF 同版、可重新编译 |
| 参考文献 | `paper_output/references.bib` | 与正文引用一致；无引用时说明原因 |
| 一键运行入口 | `src/run_all.py` 或等价脚本 | 从 documented inputs 重建核心结果 |
| 环境说明 | `requirements.txt` / `environment.yml` / 等价文件 | 版本足以复现，不只列库名 |
| 结构化结果 | `results/` | 关键指标保留完整精度，论文使用一致的舍入规则 |
| 图表 | `figures/` | 每张有源数据/绘图代码、单位、图例和可读字号 |
| 复现报告 | `qa/reproducibility.json` | 命令、版本、seed、exit code、运行时间、输入/输出 |
| 统计审查 | `qa/statistics_audit.md` | 设计、分析单位、假设、区间、稳健性与未解决风险 |
| 引用审查 | `qa/citation_audit.md` | 每条 verified/check/fix/unverifiable 状态 |
| 一致性扫查 | `qa/consistency_sweep.md` | 术语、符号、单位、数字、区间、图表/正文/摘要无漂移 |
| 页数预算 | `analysis/page_budget.json` | 摘要/官方正文/附录分账；按证据负担动态分配并回填实排页数 |
| 创新证据 | `analysis/novelty_ledger.json` | 创新类型、claim、数学/代码/对比证据和允许措辞 |
| 算法声明一致性 | `qa/algorithm_claim_consistency.json` | 名称、数学定义、代码、solver log、结果和基线映射；blocking 为 0 |
| 页结构审查 | `qa/page_structure_audit.json` | PDF 总页、摘要、官方正文、附录边界及算术校验 |
| 视觉审查 | `qa/visual_qa.md` | PDF 逐页检查结果和修复记录 |
| 互盲终审 | `qa/reviewer_1.json` ~ `reviewer_3.json`, `qa/reviewer_synthesis.md` | 初轮报告冻结；blocking concern、修复映射、最终 verdict |
| 状态与清单 | `state/decision_log.json`, `DELIVERY_MANIFEST.md` | 路径、哈希、验证状态、限制 |
| 最终交付文件夹 | `delivery/<competition>_最终交付包_vNNN/` | 正式提交候选与内部复现留档分区，含哈希和 package manifest |

`fast` 模式可以减少候选模型、文献深读和评审深度，但不能省略论文、源码、真实运行、统计边界、PDF 视觉 QA 和交付清单。

### CUMCM 2026 增补

加载 `references/cumcm_2026_compliance.md`。除上表外还必须有：

- `qa/ai_usage_log.json` 与 `qa/AI 工具使用详情.pdf`；
- AI 日志按关键实质事件聚合，覆盖所有影响模型/代码/数据/结果/结论的采用与重要纠错，不导出全量聊天；
- 参考文献之前的真实 `AI 工具使用声明`；
- 论文附录中的支撑材料文件列表和全部完整可运行代码；
- `qa/cumcm_submission_check.json`；
- `delivery/CUMCM_最终交付包_vNNN/01_正式提交/{参赛论文.pdf,支撑材料.zip}`；
- `PACKAGE_MANIFEST.json` 与本地 MD5/SHA-256。

AI 使用时，`team_led_core_modeling_confirmed`、`human_ai_review_confirmed` 和 `anonymity_confirmed` 只能依据参赛队明确确认置为 true。未确认不妨碍生成候选交付文件夹，但必须 `submission_ready=false` 并产生 `NOT_SUBMISSION_READY.md`。

## 3. 可交付性硬门

以下任一项成立时，`submission_ready` 必须为 false：

- 题目要求的附件缺失或未被使用。
- 主代码没有实际成功运行，或论文数字无法追溯到结果文件。
- 存在数据泄漏、单位错误、不可行约束、未解释的 solver failure 或未披露 synthetic 数据。
- 论文算法/模型/求解器名称与数学定义、实际代码、solver log 或结果不一致，或“改进算法”没有基线/消融证据。
- 引用虚构、DOI 指错论文或正文引用与 `.bib` 不一致。
- `TODO`、`TBD`、`AUTHOR_INPUT_NEEDED`、`[TO CONFIRM]`、`??` 等占位符仍在最终源/PDF。
- 终审仍有 blocking concern。
- PDF 未完成逐页视觉检查。
- 竞赛模板、匿名规则、页数或语言不合规。
- CUMCM 电子论文或支撑材料超过 20 MB，电子论文不是摘要首页，含承诺书/编号页，`official_body_pages` 不满足本项目维护者策略 26–28 页或页数三账不闭合，缺少完整附录、AI 声明/关键事件详情，或三项人工确认未完成。

时间不足不能把失败门改成通过；应交付“当前最佳草稿 + blocker 清单”，并清楚标记不可直接提交。

## 4. 最终校验

Stage 9 末尾先运行：

```text
python <skill>/scripts/validate_delivery.py --workspace <cwd>
```

脚本检查文件存在性、PDF 签名和大小、占位符、复现 exit code、算法声明一致性、页结构与关键 QA 文件，并生成：

- `qa/delivery_validation.json`
- `DELIVERY_MANIFEST.md`

脚本是最低机械门，不替代人工/视觉/科学判断。只有 exit code 0 且全部科学 blocking concern 已关闭，才能把 `decision_log.stages.9.submission_ready` 设为 true。

所有竞赛随后运行版本化打包；CUMCM 先生成 AI 详情：

```text
python <skill>/scripts/build_ai_disclosure.py --log <cwd>/qa/ai_usage_log.json --output <cwd>/qa/AI工具使用详情.pdf
```

然后运行：

```text
python <skill>/scripts/package_delivery.py --workspace <cwd> [--commitment <CUMCM 官方承诺书.pdf>] [--number-page <CUMCM 官方编号页.pdf>]
```

`package_delivery.py` 总会新建一个版本化文件夹，不覆盖旧包。有硬门未通过时脚本返回非零，但候选包仍保留并附 blocker 文件，便于队员继续复核后重新打包。

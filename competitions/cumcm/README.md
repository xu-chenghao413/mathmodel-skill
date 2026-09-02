# CUMCM 国赛特化层

全国大学生数学建模竞赛专用资源。当前赛年正式通知优先；规则来源和复核日期见 [`current_rules.md`](./current_rules.md)。

| 字段 | 值 |
|---|---|
| 竞赛代码 | `cumcm` |
| 官方名 | 全国大学生数学建模竞赛 |
| 时长 | 72 小时 |
| 队员 | 3 人（建模 / 编程 / 写作） |
| 语言 | 中文 |
| LaTeX 编译器 | XeLaTeX |
| LaTeX 模板 | `templates/latex/cumcm/main.tex`（本项目原创装配模板） |
| 题号 | A / B / C / D / E |
| 经验数据 | 91 份来源文档的聚合统计，其中 59 份成功文本提取 |
| 维护者策略 | `references/cumcm_2026_compliance.md`，明确标注为非官方加严门槛 |

## 文件清单

| 文件 | 用途 | 加载阶段 |
|---|---|---|
| `current_rules.md` | 官方链接和当前规则基线 | stage 0/8/9 |
| `topic_specs.json` | 题号体系与题型映射 | stage 1 |
| `rubric_overlay.json` | 国赛评分维度覆盖 | stage 8/9 |
| `empirical.json` | 聚合观察分位和样本量 | stage 8/9 |
| `empirical_notes.md` | 数据来源和局限 | 文档参考 |
| `winning_patterns.md` | 独立撰写的通用写作观察 | stage 8 |
| `phrase_bank.md` | clean-room 中文写作支架 | stage 8 |
| `distilled_*.md` | 独立撰写的结构、命名和格式观察 | 按需 |
| `anti_patterns.md` | 竞赛常见失败模式 | stage 9 |
| `abstract_template.md` | 摘要组织模板 | stage 8 |
| `paper_skeleton.md` | 电子版、正文和附录骨架 | stage 8 |

## 数据边界

本目录只公开聚合统计和独立撰写的通用规则，不公开来源 PDF、OCR 文本、论文原句、用户提供的逐页案例或项目迭代日志。任何新增样本都必须先按根目录 [`PROVENANCE.md`](../../PROVENANCE.md) 记录许可、转换方式和人工复核。


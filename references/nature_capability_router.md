# Nature Skills 融合路由

本文件把已安装的 `nature-*` 能力接入数学建模竞赛。**原始 Nature skill 目录始终只读**；所有赛题 state、代码、论文和 QA 只写入用户工作区与本 `mathmodel` skill。

## 1. 解析与调用协议

需要某个 Nature 能力时，按顺序查找：

1. 当前 Codex skills catalog 中的已安装路径；
2. `$HOME/.agents/skills/<skill>/SKILL.md`；
3. `$HOME/.codex/skills/<skill>/SKILL.md`；
4. `$HOME/.claude/skills/<skill>/SKILL.md`。

找到后必须完整读取它的 `SKILL.md`，再按其 manifest/路由只加载本次需要的 fragments/references。遵守其确认门、工具限制、输出合同与 QA。找不到时记录 `execution.nature_router.degraded`，使用本 skill 的本地合同继续；不得为了“融合”修改、复制或修补 Nature skill。

竞赛题面、官方规则、用户明确要求和 `competitions/<comp>/` 模板优先于期刊风格。Nature skills 提供的是证据、统计、制图、写作与审查纪律，不能把竞赛论文强制改成 Nature 期刊体例。

## 2. 主链能力

| 能力 | 触发阶段 | 用法与边界 | 交付记录 |
|---|---|---|---|
| `nature-academic-search` | 0/3/4/8 | 定向查方法、领域假设、数据定义与官方标准。优先原始论文/官方文档，多源去重；不做无边界大搜。 | `evidence/search_log.*`, claim-evidence ledger |
| `nature-statistics` | 5/6/9 | 检查分析单位、数据切分、独立重复、模型假设、效应量/区间、误差与多重比较；用户已提供原始赛题数据并要求求解时可做数据支持的重分析。 | `qa/statistics_audit.md` |
| `nature-figure` | 5/6/8/9 | 数据图和多面板图。后端由 `decision_log.execution.plot_backend` 显式传入，默认沿用代码后端；Autopilot Python 管线即明确选择 Python。禁止用 AI 图替代定量数据图。 | figures、绘图源码、`qa/figure_qa.md` |
| `nature-writing` | 8 | 以 `journal=generic` 和竞赛语言运行，借用 claim-evidence-boundary、Results 主线压缩和缺失输入占位规则；章节、页数、摘要、Letter 仍服从竞赛模板。 | section drafts、claim map |
| `nature-polishing` | 8/9 | 术语/数值/单位一致性扫查、中文或英文润色、LaTeX 版面修复。不得强化证据边界或添加不存在的结果。 | `qa/consistency_sweep.md`, layout QA |
| `nature-ref-verifier` | 8/9 | 对最终参考文献逐条做 DOI/题名/作者/年份/卷期页字段校验并修正 `.bib`；中文来源用可用的中文数据库或官方页降级。 | `qa/citation_audit.md` |
| `nature-reviewer` | 9 | 采用 3 份互盲报告 + 事后 synthesis。评审包只含不可变论文/代码/图表/竞赛 rubric；三个 emphasis brief 见 `feedback_layer3_panel.md`。 | `qa/reviewer_1..3.json`, `qa/reviewer_synthesis.md` |

## 3. 条件增强

| 能力 | 何时使用 | 默认行为 |
|---|---|---|
| `nature-reader` | 方法推导必须依赖某篇全文，或用户提供待精读论文 | 仅处理论文，不把赛题 PDF 强制做成双语 paper reader；优先复用已有 source map |
| `nature-paper-card` | championship 模式需深挖 1–3 篇关键方法论文的公式、证据边界或可迁移模块 | 只做关键论文，不批量生成卡片 |
| `nature-downloader` | 元数据/摘要不足，且合法全文对结论确有必要 | 其 SI confirmation gate 会打断 Autopilot，因此默认不下载；只有用户已明确 SI/正文偏好或确认后调用 |
| `nature-citation` | 用户明确要求 Nature/CNS 范围的支撑文献 | 一般竞赛引用不限制 CNS，默认改用 academic-search + ref-verifier |
| `nature-data` | 需要数据/代码可用性声明、仓库计划或 FAIR 元数据 | 普通竞赛默认只借用数据 provenance ledger，不强制写期刊式声明 |
| `nature-paper2ppt` | 用户明确要求答辩/汇报 PPTX | 在论文交付完成后作为附加产物，不阻塞核心提交包 |

## 4. 默认不接入

- `nature-literature-pipeline`：面向日常定时推送，不适合 3–4 天赛程。
- `nature-experiment-log`：面向实验室样品/设备日志，和竞赛 decision log 语义不同。
- `nature-image2ppt`：用于图片型 PPT 还原，不用于从赛题生成新演示。
- `nature-paper-to-patent`：专利交底与竞赛交付无关。
- `nature-response`：返修/审稿回复，不是赛前终审。

用户明确提出对应附加任务时，可以在数学建模主交付完成后单独路由；不得把它们塞进默认主链。

## 5. 共享数据结构

无论具体 Nature skill 的输出格式如何，主流程都要归一化为：

```json
{
  "capability": "nature-statistics",
  "stage": 6,
  "status": "used|skipped|degraded|blocked",
  "inputs": ["relative/path"],
  "outputs": ["relative/path"],
  "blocking_findings": [],
  "limitations": [],
  "timestamp": "ISO-8601"
}
```

追加到 `decision_log.execution.nature_router`，不要把大段报告塞进 state；state 只存摘要和路径。

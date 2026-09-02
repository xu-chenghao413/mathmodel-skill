# Autopilot — 从赛题到可交付包

本协议在用户**已经提供赛题文本、PDF、图片或附件路径**并要求完成建模/论文/交付时启用。它覆盖各 stage 中的常规暂停与编号确认；`guided` 模式仍按原 stage 文档逐步问答。

## 1. 入口与优先级

- 直接给出一套赛题材料 → `execution.interaction_mode = autopilot`。
- 只说“开始建模”、题目尚未公布、要求教学式协作 → `guided`。
- 已有 `state/decision_log.json` → 恢复其中模式，不擅自切换。
- 用户明确指定竞赛、题号、语言、模型或输出格式时，用户选择高于自动推断。
- 本协议只减少交互，不放松真实性、授权、复现性和交付 QA。

Autopilot 中的普通选择一律采用“当前证据下的推荐项”，把选择、理由、备选和置信度写入 `decision_log` 后继续。不要逐阶段请求确认。

## 2. 仅允许暂停的硬阻塞

只有以下情况可以向用户提问并暂停：

1. 赛题文件损坏、不可读，且没有可替代文本。
2. 题目明确依赖某附件，但附件未提供或无法定位。
3. 无法可靠判定竞赛模板，且错误模板会使最终提交不合规。
4. 需要登录、付费、验证码、API 密钥或其他新授权。
5. 两种解释会产生实质不同的模型或结论，题面本身无法消歧。
6. 继续只能伪造数据、结果、引用或实验。
7. CUMCM 要标记为“可直接提交”但参赛队尚未明确确认核心建模主导、AI 内容逐项人工核验或匿名检查。此时先完成候选交付文件夹，只在最终 ready 判定前询问，不阻塞前面建模与打包。

缺少队员信息、截止时间、偏好或非关键背景不是阻塞。使用保守默认值并记录假设。

## 3. 初始化

解析 `<skill>` 后，由 agent 自动运行：

```text
python <skill>/scripts/bootstrap_run.py --workspace <cwd> --mode autopilot \
  --competition <cumcm|mcm|diangong|auto> --problem <题目路径> \
  [--attachment <附件路径> ...]
```

脚本只初始化目录和 state，不替代读题。若已有 state，先读取并使用 `--resume`，禁止覆盖已有决策。

建立不可变 source packet：赛题原件、附件清单、文件哈希、解析状态、竞赛/题号/语言推断与置信度。原始数据只读；清洗结果写入 `data_processed/`。

## 4. 一次贯通 10 阶段

| Stage | Autopilot 动作 | 必须落盘的证据 |
|---|---|---|
| 0 | 读取全部题面和附件，环境预检，锁定竞赛模板；CUMCM 锁定 2026 合规基线与当前赛年覆盖文件 | source packet、问题预扫、工具状态、compliance state |
| 1 | 单题直接锁题；多题按矩阵自动选最高可交付性题目 | 选题矩阵、拒绝理由、风险 |
| 2 | 建 source map、要求矩阵、数据 schema、子问依赖图 | `analysis/requirements_matrix.md` 或等价文件 |
| 3 | 至少三类候选；必要时定向检索方法证据；跑 toy demo | 候选矩阵、文献证据、toy demo 日志 |
| 4 | 固化假设、符号、单位和术语 ledger | assumption / notation / terminology artifacts |
| 5 | 每个 Qi 写公式、可运行代码、结果、基线、图表和解释 | 源码、运行日志、结构化结果、图表 |
| 6 | 做与数据生成机制相符的验证、联合扰动和失效边界 | statistics audit、稳健区间、失稳预警 |
| 7 | 用证据限定优点、缺点、适用范围和推广 | claim-boundary ledger |
| 8 | 按竞赛模板组装论文；验证引用；统一图表与术语；CUMCM 生成 AI 声明/详情；编译 | `.tex`、`.bib`、PDF、citation audit、AI audit |
| 9 | 互盲终审、定向修复、重跑、PDF 视觉 QA、交付校验并生成单一版本化文件夹 | reviewer reports、QA reports、manifest、delivery package |

若某 stage 的 L1 verdict 为 `refine` 或 `refine_partial`，Autopilot 自动执行推荐的最小范围 patch，最多 3 次；只有 `block` 才暂停。`carryover` 必须进入最终 blocker 清单，不能静默标记 submission-ready。

## 5. 运行与复现纪律

- 所有主要数值必须来自实际执行的代码，不得由语言模型手算后伪装成运行结果。
- 保存真实执行命令、工作目录、Python/R 版本、依赖、随机种子、开始/结束时间和 exit code 到 `qa/reproducibility.json`。
- 训练/验证/测试、时间序列切分、交叉验证、模拟重复和技术重复必须区分；禁止数据泄漏。
- 没有真实数据时可以生成“仅用于管线检查”的 synthetic smoke test，但不得把它写成赛题结论。
- 每个关键结论必须能回指到题面/数据、代码、结果表/图或已验证引用。

## 6. 完成定义

“完成”不是写完正文，而是同时满足：

1. 主代码从干净入口可复跑，exit code 为 0。
2. 结果、图表、摘要与正文数值一致，无手工漂移。
3. 引用元数据已核验；无法核验的条目被明确标记而非伪造。
4. 统计/稳健性审查通过，或真实限制已写入论文。
5. PDF 编译成功并逐页视觉检查，无裁切、乱码、空白页、`??` 或未解决占位符。
6. 终审的 blocking concerns 已解决。
7. `scripts/validate_delivery.py --workspace <cwd>` 返回 exit code 0。
8. `DELIVERY_MANIFEST.md` 列出全部交付物、哈希、验证状态和已知限制。
9. 最终产物整理进 `delivery/<competition>_最终交付包_vNNN/`，正式提交候选与内部复现留档分开。
10. CUMCM 通过 2026 格式/20 MB/AI/匿名/附录门；队员未完成法定人工确认时，交付包保留但必须含 `NOT_SUBMISSION_READY.md`。

最后只向用户汇报交付包路径、核心结论、验证结果和仍需人工提交前确认的事项；不要把中间 prompt 当成交付物。

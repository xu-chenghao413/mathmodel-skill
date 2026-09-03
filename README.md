# mathmodel-skill

[![Version](https://img.shields.io/badge/version-v7.3.3-blueviolet)](./CHANGELOG.md)
[![CI](https://github.com/xu-chenghao413/mathmodel-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/xu-chenghao413/mathmodel-skill/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](./LICENSE)

面向 CUMCM、MCM/ICM 与电工杯的端到端数学建模竞赛工作流。它把赛题解析、模型选择、真实代码求解、统计与稳健性、图表、论文、合规检查和最终交付组织成可恢复的 10 个阶段。

提供赛题和附件时默认进入 **Autopilot**，连续运行到可验证的交付包；只说“开始建模”或明确要求逐步协作时进入 **Guided Mode**。

> 本项目协助团队组织和核验工作，不保证获奖，也不会在缺少题面、数据或真实运行结果时补造结论。

## 主要能力

- 三类竞赛共用状态协议，并按竞赛加载规则、模板和评分覆盖层。
- `fast`、`standard`、`championship` 三种分析深度，与 Autopilot/Guided 独立组合。
- 每个子问题形成 `数据 → 预处理 → 模型 → 结果 → 回题结论` 的可复现链路。
- 自适应正文页预算、创新证据账本及算法名称—定义—代码—日志—结果一致性检查。
- CUMCM AI 使用记录、匿名检查、PDF 视觉 QA、交付清单和版本化打包。
- 可选调用分别安装的文献、统计、科研绘图、写作和审稿 skills；缺少这些扩展时核心流程仍可运行。

## 支持范围

| 竞赛 | 默认时长 | 语言 | LaTeX 基线 | 经验数据状态 |
|---|---:|---|---|---|
| CUMCM | 72 h | 中文 | XeLaTeX / 本项目原创 `ctexart` 装配模板 | 91 份来源文档的聚合统计，其中 59 份成功文本提取 |
| MCM/ICM | 96 h | English | pdfLaTeX / `article` | `seed v0.1`，不宣称论文样本分位 |
| 电工杯 | 72 h | 中文 | XeLaTeX / `ctexart` | `seed v0.1`，不宣称论文样本分位 |

当届题面、官方通知和用户明确要求始终优先于仓库内的历史基线。

## 60 秒开始

### Codex skill

```bash
git clone https://github.com/xu-chenghao413/mathmodel-skill.git ~/.agents/skills/mathmodel-skill
python -m pip install -r ~/.agents/skills/mathmodel-skill/templates/shared/requirements.txt
cd <your-team-workspace>
codex
```

然后提供赛题和附件，并说：

```text
使用 $mathmodel-skill 完成这道赛题，生成可验证、可复现的最终交付包。
```

项目级安装：

```bash
mkdir -p .agents/skills
git clone https://github.com/xu-chenghao413/mathmodel-skill.git .agents/skills/mathmodel-skill
```

Windows PowerShell 可将目标目录换成：

```powershell
git clone https://github.com/xu-chenghao413/mathmodel-skill.git "$HOME/.agents/skills/mathmodel-skill"
py -m pip install -r "$HOME/.agents/skills/mathmodel-skill/templates/shared/requirements.txt"
```

仓库同时保留 Claude Code 的 `SKILL.md` 入口和跨 harness 状态协议。状态默认写入当前赛题工作区的 `state/decision_log.json`，不会写入本 skill 仓库。

## 工作流

1. Source packet 与环境启动
2. 多题比较与选题
3. 问题拆解和依赖分析
4. 模型候选比较
5. 假设、符号和术语基线
6. 逐子问题真实求解
7. 统计、灵敏度与稳健性
8. 模型评价与推广
9. 证据化论文写作
10. 互盲终审、PDF QA 与版本化交付

详细执行协议见 [`SKILL.md`](./SKILL.md)。

## CUMCM 官方规则与维护者策略

仓库明确区分两层约束：

- `competitions/cumcm/current_rules.md` 记录可核验的官方基线及来源链接；使用前必须复核当届通知。
- `references/cumcm_2026_compliance.md` 还包含本项目有意采用的、更严格的维护者策略。

其中“摘要恰好 1 页、官方正文控制在 26–28 页、附录采用 A/B/C 三段”等是**本项目的交付策略，不是 CUMCM 官方新增规则**。当前公开官方基线仍是摘要原则上不超过一页、正文不超过 30 页。若当届正式通知或用户要求发生冲突，以前者为准。

## 目录结构

```text
.codex-plugin/plugin.json       # plugin manifest
agents/openai.yaml              # skill UI 元数据
skills/mathmodel-skill/         # plugin 入口 shim
SKILL.md                        # 主工作流入口
AGENTS.md                       # 项目级 harness 说明
competitions/<comp>/            # 竞赛规则、模板和经验层
references/                     # 按阶段懒加载的工作流合同
scripts/                        # 初始化、评分、渲染、验证和打包工具
templates/latex/                # 本项目原创 LaTeX 装配模板
templates/shared/               # 状态和交付模板
tests/                          # 自动化测试
```

Codex skill 与 plugin 的组织方式分别对齐 [OpenAI Skills 文档](https://learn.chatgpt.com/docs/build-skills) 和 [Plugin 打包文档](https://developers.openai.com/plugins/build/plugins)。

## 数据、来源与隐私边界

公开仓库只保留维护者编写的工作流、模板、聚合统计和来源说明：

- 不提交来源论文 PDF、论文原文、付费材料或登录后取得的文件；
- 不提交用户提供的未公开论文、逐页案例数据、评审记录或项目迭代日志；
- `distilled_*.md` 只保留从聚合观察重新独立撰写的通用规则，不作为论文原句库；
- 外部规则、论文、数据集和网站不会因本仓库采用 MIT 而被重新许可。

完整边界和维护流程见 [`PROVENANCE.md`](./PROVENANCE.md) 与 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)。

## 设计影响与可选集成

本项目受到通用数学建模工作流以及已安装 `mcm`、`nature-*` skills 的流程思想启发。v7.3.3 公开版只保留独立编写的实现和一般性方法，不打包这些外部 skills 的源码、文档或资产。

`nature-*` 在本项目中只是可选能力路由名称，不表示与 Springer Nature、相关 skill 作者、OpenAI 或 Anthropic 存在隶属、认可或联合发布关系。各外部 skill 继续适用其自己的许可证和使用条件。

署名说明不是第三方代码的使用授权；后续若要引入外部实现，必须先记录来源、版本和兼容许可证。

## 开发与验证

```bash
python -m unittest discover -s tests -v
python scripts/doctor.py
```

提交前还应检查：

- 版本号在 README、`SKILL.md`、`AGENTS.md` 与 plugin manifest 中一致；
- 仓库和完整 Git 历史不存在论文 PDF、用户案例或未授权模板；
- 所有 JSON/YAML 可解析，测试全绿，示例命令能在干净环境运行。

贡献方式见 [`CONTRIBUTING.md`](./CONTRIBUTING.md)，安全问题见 [`SECURITY.md`](./SECURITY.md)，版本变化见 [`CHANGELOG.md`](./CHANGELOG.md)。

## License

除另有说明外，本仓库中由维护者原创的代码、文档和模板采用 [MIT License](./LICENSE)。MIT 不覆盖竞赛规则、论文、数据集、商标、外部 skills 或其他第三方材料；具体说明见 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md)。

历史文件若保留其他作者的 MIT 署名，按文件中的通知和 [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md) 处理；本项目不将这些历史部分冒称为当前维护者原创。

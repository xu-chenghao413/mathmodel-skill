# Quickstart：合成数据端到端示例

这个示例不需要第三方 Python 依赖，用一条命令生成一个可检查的最小交付包：

```bash
python examples/quickstart/run_demo.py --output demo-output
```

Windows PowerShell 也可以使用 `py` 替代 `python`。再次运行时，请显式加 `--force`；脚本默认拒绝覆盖已有目录。

## 生成的产物

```text
demo-output/
├── input/                  # 题面和合成原始数据
├── state/decision_log.json # 阶段状态与关键决策
├── analysis/model_card.json# 假设、公式和模型边界
├── results/allocation.csv  # 区域级分配结果
├── results/summary.json    # 总量、占比和校验摘要
└── qa/manifest.json        # SHA-256 文件清单和可提交状态
```

示例刻意保持离线、确定性和可审计：它不是对真实竞赛结果的承诺，也不会把输出写回 skill 安装目录。更完整的竞赛工作流仍由根目录的 `SKILL.md` 驱动。

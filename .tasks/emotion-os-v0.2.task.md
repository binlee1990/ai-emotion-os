Task format: 2
Objective: ai-emotion-os v0.2：①引擎能力补全（调节力并入状态项、下行比较安慰/优越、wanting/liking 独立动机环路含「上头」、安全框架平滑过渡、+6 新类别）②领域参数标定（倒U拐点、习惯化速率、唤醒残余窗、λ、峰终权重——文献检索替换「待标定」常数）③NL→Event 适配器（LLM 结构化输出契约+解析校验，零依赖可测）④四领域场景扩展（短剧循环/游戏四钥匙与抽卡/音乐 BRECVEMA 可表达子集/§6.2 泛用矩阵）。用户已拍板：三方向全做、四领域全扩展、保持纯目录、完成后同 v0.1 单一提交惯例。
Scope: 输入=v0.1 代码（c4ade0a）+调研.md；允许改 emotion_os/、tests/、docs/；不加运行时第三方依赖、不做真实 LLM 网络调用（测试用 fixture）；不动 research/。
Success criteria: (1) pytest 全量 0 失败，新增 ≥4 个场景文件且断言来自调研 §5/§6.2 预测；(2) 标定常数在代码中附文献出处（或维持默认并注明未找到）；(3) 适配器从 JSON 文本构造 Event 并全管线贯通（fixture 驱动）；(4) fresh 复审无 P0。
Verification: python -m pytest tests/ -q；grammar G3+引用图 G4 在更新后的 docs 重跑；复审子代理结论；最终单一 commit。
Progress: 已完成（2026-11-08）。图 TG-20261108T2235-7b4ecda30792 全部 9 节点关闭、总目标 4 判据有证据（overall: COMPLETE，复审返工 1 轮）。交付：引擎 88 类别+wanting/liking 双池+安全坡+耗竭入调节力；常数注记经复审核验（λ 出处已按 Walasek 2024/Brown et al. 2024 更正；倒U顶点与习惯化速率文献无值、如实标自设）；NL→Event 适配器（契约+校验+围栏剥离+宽容布尔，13 项测试含端到端）；4 个新场景文件 23 项断言；全量 115 passed、G3/G4 通过；fresh 复审无 P0（P1×2/P2×7 全修）。调研.md 两处引文勘误记入架构合同 §8。

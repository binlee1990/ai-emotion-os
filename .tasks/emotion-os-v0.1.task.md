Task format: 2
Objective: 基于研究/research 人类情绪全景调研.md 的知识基础，交付 ai-emotion-os v0.1——一个「事件 → 评价 → 情绪 → 动力学 → 表达」的可计算情绪引擎（Python 库），并以调研中取样的场景（打脸/恐怖倒U/重逢/BE/悬念/羡慕分流/RPE）验证知识库的可用性。用户指令：使用 meta-theory-planner 生成方案栈、task-graph 拆解并全力执行。
Scope: 输入=调研.md（唯一知识来源，引用其章节号）；允许新建 docs/、emotion_os/、tests/、README.md；不改动 research/；不做 LLM 集成、界面与性能优化（v0.1 范围外）；Python ≥3.11、零运行时第三方依赖、pytest 验证。
Success criteria: (1) pytest 全量 0 失败，含 ≥6 个场景测试按调研预测断言情绪类别/强度关系；(2) 方案栈一致（grammar fitness G3 + 文档引用 G4 通过）；(3) fresh-context 复审无 P0 意见；(4) 表达层输出中文分级词表 + 4D 维度双通道。
Verification: python -m pytest tests/ -q（全量）；python <mtp>/scripts/grammar_fitness_test.py --grammar docs/grammar/appraisal-grammar.yaml；python <mtp>/scripts/variance_diff.py --reference-graph --doc-root docs；复审子代理结论。证据落图状态与本文 Progress。
Progress: 已完成（2026-11-08）。图 TG-20261108T2147-c06ca22f7890 全部 11 节点关闭、总目标 4 判据有证据（overall: COMPLETE）。交付：docs/ 方案栈（架构合同+领域规则 10 条，G3/G4 门通过）、emotion_os 包（8 模块、82 类别目录含 9 个中文特有词）、tests/ 76 项测试（8 单元文件+7 场景）全绿、fresh 复审无 P0（5 项 P1 已修复回归，其中 R-APP-02 罚错对象与 R-APP-03 羡慕→幸灾乐祸跨事件链为复审驱动的真实语义补全）。看板 .tasks/kanban.html。未决项=代码未提交（用户未要求 commit）；v0.2 候选见架构合同 §8。

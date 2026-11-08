Task format: 2
Objective: ai-emotion-os v0.6：中文词表语域分级（正式度/场合）——调研附录最后一项表达层未决项。单语域轴三档 formal（书面/对外正式场合）/ neutral（通用，默认=现状输出不变）/ colloquial（口语/对内私下场合）；Expressor.describe 与 graded_word 增 register 参数，未覆盖类别回退 neutral。语域覆盖按「语域差异显著+高频」选 ~25 类别；正式度标注为语言常识自设（2026-11-09 检索：无现成汉语情绪词语域分级规范研究——AANC 为年龄差异维度、极性词库无正式度轴；与 v0.2 参数标定同款诚实注明）。
Scope: 输入=v0.5（da22f28，已推送）；允许改 emotion_os/expression/、tests/、docs/、README、.tasks；不加运行时依赖；grammar R-EXP-01 更新（双通道+语域）。
Success criteria: (1) 同一状态三种语域输出不同词且 formal 无口语标记词（麻了/笑死/磕疯了等全量断言）；(2) 未覆盖类别回退 neutral；(3) 默认参数向后兼容（不传 register 输出与 v0.5 一致——现有 155 测试不动全绿）；(4) 场景断言：正式场合表达 vs 私下口语表达；(5) pytest 全量 0 失败；fresh 复审无 P0。
Verification: python -m pytest tests/ -q；G3/G4 门。
Progress: 实现与验证完成：lexicon 语域梯（15 formal+13 colloquial，整梯替换档位对齐，非法值 ValueError）+ Expressor/graded_word register 透传（默认 neutral=v0.5 行为不变，既有 155 测试零改动全绿）+ 7 项新测试（含 formal 无口语标记词全量断言）+ demo 三语域对照（破防：心理防线被击穿/破防了/绷不住了）+ R-EXP-01 更新与架构合同 §8 转已修（自设标注声明）；162 passed、G3/G4 通过。fresh 复审无 P0/P1（4 项 P2 全修：口径统一 30 条梯/28 类别、删死循环、补 formal 真词激活测试、fear/dread 补 formal 梯消除「发怵」经回退泄漏+README 回退限定）；163 passed。待提交推送。

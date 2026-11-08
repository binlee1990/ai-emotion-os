Task format: 2
Objective: ai-emotion-os v0.5：适配器层 goal id 契约化——修 v0.4 复审观察的静默零效应（真实 e2e 中 LLM 抽取自由格式 goal id 如「方案获认可与署名」，与 profile 目标词表不匹配 → R-INT-01 正确归零但整段叙事情绪失联）。方案与 v0.4 同模式：NLEventAdapter 增 goal_ids/goal_aliases 参数——adapt 时抽取 prompt 注入 agent 目标名单（主防线），parse 后 goal_impacts 键经别名映射，映射后仍表外的键保留原样但 warning 可见化（引擎语义不变：表外 goal 零相关是正确行为）。
Scope: 输入=v0.4（196adb2，已推送）；允许改 emotion_os/adapters/、tests/、examples/、docs/、README；引擎层（appraiser 的 goal_importance 词表匹配）不动；零第三方依赖；e2e 沿 v0.3 授权（claude/codex CLI 无副作用文本调用）。
Success criteria: (1) fixture（无 LLM）：表外 goal id 经别名映射后引擎激活（对照不映射的零激活）；(2) prompt 注入目标名单可断言；(3) 映射后仍表外的键产生 warning；(4) 真实 e2e 复跑：claude 侧 goal_impacts 键落在 profile 词表（至少主键）；(5) pytest 全量 0 失败；fresh 复审无 P0。
Verification: python -m pytest tests/ -q；examples/llm_e2e.py 复跑日志；G3/G4 门。
Progress: 已完成（2026-11-09）。交付：goal_ids prompt 注入（主防线）+ map_goal_impacts 共享函数（别名映射→命中词表改写原键→表外键 warning→同键合并含零值角）+ null 值宽容为省略（codex 实测 "novelty":null）；10 项测试（含 canonicalize 改写字面命中断言、零值角、端到端对照映射激活 vs 未映射零激活——复审变异测试证实区分力）；真实 e2e 两家 goal_impacts 键全部落回 esteem、claude 事件2 shuang(1.00)+jie_qi(0.93)；fresh 复审无 P0/P1（4 项 P2 全修：原键改写、零值角、e2e 双实现归一为共享函数、状态文件）；153→155 passed。待提交推送。

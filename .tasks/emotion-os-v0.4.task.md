Task format: 2
Objective: ai-emotion-os v0.4：适配器层跨事件实体规范化——修 v0.3 LLM 端到端实测缺口（同一实体不同写法「主管」vs「supervisor」→ charges 字面匹配不命中 → 解气不触发）。方案：EntityResolver（别名表注入+已见实体登记+归一）+ NLEventAdapter 可选挂载（prompt 注入已见实体名单让 LLM 复用写法 + parse 后实体字段兜底归一）。
Scope: 输入=v0.3（da78a17，已推送）；允许改 emotion_os/adapters/、tests/、examples/、docs/、README；引擎层（charges 字面匹配语义）不动；零第三方依赖；e2e 验证仅限 claude/codex CLI 无副作用文本调用（沿 v0.3 授权）。
Success criteria: (1) fixture 双事件不同写法（无 LLM）经 resolver 归一后引擎触发解气；(2) prompt 注入实体名单可断言；(3) group:/fictional: 前缀保留；(4) 真实 e2e 复跑：事件2 justice_target 与事件1 violator 归一一致且解气触发（至少 claude 侧）；(5) pytest 全量 0 失败；fresh 复审无 P0。
Verification: python -m pytest tests/ -q；examples/llm_e2e.py 复跑日志；G3/G4 门。
Progress: 实现与验证完成：EntityResolver（别名表+已见登记+归一，保留字/前缀边界，无模糊匹配）+ NLEventAdapter 挂载（roster prompt 注入主防线 + parse 后归一兜底）+ 8 项测试（含 fixture 双事件端到端 jie_qi>0.3 回归）+ e2e 复跑（claude 侧 roster 注入下 justice_target=主管、jie_qi=0.69 触发——v0.3 缺口修复实证）；142 passed；README/架构合同已更新。fresh 复审无 P0/P1（3 项 P2 全修：别名键归一、violator str 化、保留字小写归一；另补 goal id 枚举 backlog）；145 passed。已完成并推送。

Task format: 2
Objective: ai-emotion-os v0.3：①OSF 实证标定倒U顶点（Andersen 2020 原始数据拟合 FEAR_ENJOYMENT_PEAK，自设值→实值；下载失败则如实 NOT RUN）②真实 LLM 端到端（用户已授权 claude CLI + codex CLI；按模型路由 SOP：结构化抽取取各家轻量档 claude=haiku、codex=gpt-6-luna+low，双供应商交叉）③引擎场景扩展至 §5.6 运动/§5.7 社交（BIRGing/CORFing/绝杀/跑者高潮/FOMO/已读不回/热搜义愤）④examples/demo_story.py 端到端验收演示（fixture 驱动叙事→情绪轨迹可读输出）。
Scope: 输入=v0.2（8a1a71c，已推送）；允许改 emotion_os/、tests/、examples/、docs/、.tasks/；OSF 数据为外部下载物放 .tasks/osf-andersen/（不信任数据，分析脚本不与之间目录执行）；CLI 调用仅限 claude/codex 无副作用文本生成；不动 research/（勘误已完成并另行提交）。
Success criteria: (1) pytest 全量 0 失败（新增运动/社交场景 ≥6 断言）；(2) FEAR_ENJOYMENT_PEAK 要么带拟合值+出处+复现脚本，要么维持 0.30 并注明 NOT RUN 原因；(3) 两家 CLI 真实调用各 ≥1 次成功贯通「叙事→Event→引擎→中文表达」并留证据；(4) demo 可离线运行且输出可读轨迹表；(5) fresh 复审无 P0。
Verification: python -m pytest tests/ -q；examples/demo_story.py 实跑输出；.tasks/llm-e2e-log.md 记录 CLI 原始返回与管线输出；G3/G4 门。
Progress: N1–N5 完成（N1 OSF 拟合 0.84 已入库+复现脚本；N2 双 CLI 贯通 2/2——codex 位置参数长 prompt 在 Windows 被截断已定位并改 stdin 传递，证据 .tasks/llm-e2e-log.md；N3 运动/社交 6 方法 16 断言+grammar R-DYN-03；N4 demo_story 8 事件轨迹表；N5 全量 130 passed+G3 11规则+G4 0断链）。当前动作=N6 fresh 复审（后台进行中）。提交计划：research 勘误独立提交 + v0.3 单一提交。

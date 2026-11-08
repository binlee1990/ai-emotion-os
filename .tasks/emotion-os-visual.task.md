Task format: 2
Objective: ai-emotion-os 整体可视化界面：以引擎真实输出驱动（Python 侧跑 demo 叙事导出 JSON，前端只呈现不重实现），单页自包含 HTML——呈现①引擎五阶段管线（事件→评价→生成→动力学→表达）②8 事件弧线轨迹（词×强度、4D、心情、峰终记忆——demo_story 数据）③语域三档对照（v0.6）④核心机制（倒U实证顶点 0.84、峰终定律）。设计走 /frontend-design 方向 + /visual-craft 制作规范；发布为 Artifact（给别人看的完成作品），仓库保留生成脚本可复现。
Scope: 输入=v0.7（6440db3）；新增 examples/generate_visualization.py（引擎→JSON→自包含HTML）与产物 HTML；不改 emotion_os/ 运行时；数据必须来自引擎真实调用（不得手写编造数值——机制示意图除外且须标注）。
Success criteria: (1) HTML 离线自包含打开可用（无外部网络依赖或仅 CDN 白名单）；(2) 页面数值与引擎实际输出一致（抽查 3 处核对）；(3) 覆盖管线/轨迹/语域/机制四板块；(4) 移动端可用宽度；(5) 生成脚本可重复运行产出等价页面。
Verification: python examples/generate_visualization.py 实跑；浏览器/结构核验；数值抽查对照引擎输出。
Progress: 已完成：单页自包含 HTML（docs/visualization.html，28KB，零外部请求）+ 生成器 examples/generate_visualization.py + 模板 examples/visual_template.html。四板块全覆盖（管线解剖/八幕弧线竖排宋体词/语域三档/倒U实证曲线）；数值抽查一致（memory 0.459↔demo +0.46、三语域串一致）；1280 与 390 双端截图实看三轮（修竖排词重叠、SVG 字体属性 var() 不解析、移动端宽图表横滚、删首帧入场动画）；设计：冷纸白+正朱负靛双色温+宋体 display。Artifact 发布通道不可用（会话为 ANTHROPIC_AUTH_TOKEN 认证，需 claude.ai 登录）——仓库交付完整。待提交推送。

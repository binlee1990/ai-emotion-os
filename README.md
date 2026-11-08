# ai-emotion-os

基于评价理论的「事件 → 评价 → 情绪」可计算情绪引擎（Python 库）。知识基础与理论依据见 [research/人类情绪全景调研.md](research/人类情绪全景调研.md)；设计与接口合同见 [docs/architecture-contract.md](docs/architecture-contract.md)；整体可视化见 [docs/visualization.html](docs/visualization.html)（引擎真实输出驱动，`python examples/generate_visualization.py` 重新生成）。

安装（Python ≥3.10，零运行时依赖）：

```bash
pip install -e .          # 本地可编辑安装（发布 PyPI 后可用 pip install ai-emotion-os）
```

```python
from emotion_os import EmotionEngine, AgentProfile

engine = EmotionEngine(AgentProfile.neurotic_example())
result = engine.process(event, dt_minutes=1.0)   # → 状态 + 中文分级词表 + 4D 维度双通道
```

语域分档（v0.6）：表达按场合选词——对外正式（formal）避口语/网络语，私下（colloquial）避书面成语腔，默认 neutral。语域梯覆盖高频差异类别，**未覆盖类别回退 neutral**（formal 场合下回退词可能仍带口语色彩）：

```python
out = engine.expressor.describe(engine.state, register="formal")    # 或 "colloquial"
```

同一状态：formal「又心理防线被击穿又感动」/ neutral「又破防了又感动」/ colloquial「又绷不住了又感动」。

自然语言入口（v0.2）：注入任意 LLM 调用即可把叙事文本转成事件——

```python
from emotion_os.adapters import NLEventAdapter
adapter = NLEventAdapter(llm_call=my_llm)        # Callable[[str], str]：prompt 进，JSON 出
event = adapter.adapt("反派当众羞辱主角").event   # → Event，经引擎全管线
```

跨事件实体规范化（v0.4）：LLM 对同一实体可能输出不同写法（`主管` vs `supervisor`），
导致跨事件机制（解气的 charges 匹配）失联。挂 `EntityResolver` 双防线——
prompt 注入已见实体名单（LLM 复用写法）+ parse 后别名/已见归一（兜底）：

```python
from emotion_os.adapters import EntityResolver, NLEventAdapter
resolver = EntityResolver(aliases={"supervisor": "主管"})   # 领域别名表可选
adapter = NLEventAdapter(llm_call=my_llm, resolver=resolver)
```

goal id 契约化（v0.5）：LLM 抽取自由格式 goal id（如「方案获认可与署名」）会与
profile 目标词表失联而静默零效应。注入词表让 LLM 用合法键 + 别名映射兜底 +
表外键 warning 可见化：

```python
adapter = NLEventAdapter(llm_call=my_llm, goal_ids=list(agent.goals),
                         goal_aliases={"方案获认可与署名": "esteem"})
```

CLI 供应商包装（v0.3，真实端到端）：`claude_cli_call` / `codex_cli_call` 开箱注入——

```python
from emotion_os.adapters import claude_cli_call, NLEventAdapter
event = NLEventAdapter(llm_call=claude_cli_call).adapt("反派当众羞辱主角").event
```

- 演示：`python examples/demo_story.py`（离线 8 事件弧线轨迹表）；
  `python examples/llm_e2e.py`（双 CLI 供应商真实端到端，CLI 缺席自动 SKIP）
- 领域规则（评价→情绪映射合同）：[docs/grammar/appraisal-grammar.yaml](docs/grammar/appraisal-grammar.yaml)
- 参数标定：倒U顶点 `FEAR_ENJOYMENT_PEAK=0.84` 由 Andersen 2020 OSF 开放数据拟合
  （Likert 7.55/9，换算假设 `fear_engine = fear_likert/9`；delta-method 95% CI [0.59, 1.09]；
  复现脚本 [scripts/fit_fear_enjoyment_peak.py](scripts/fit_fear_enjoyment_peak.py)）
- 测试：`python -m pytest tests/ -q`（162 项：单元 + 短剧/游戏/音乐/运动/社交等 12 个场景）
- 任务状态：[.tasks/emotion-os-v0.6.task.md](.tasks/emotion-os-v0.6.task.md)（v0.1–v0.5 见同目录）

范围：结构化事件输入的研究原型；运行时配置与未决项见架构合同 §8。

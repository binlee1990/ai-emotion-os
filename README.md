# ai-emotion-os

基于评价理论的「事件 → 评价 → 情绪」可计算情绪引擎（Python 库）。知识基础与理论依据见 [research/人类情绪全景调研.md](research/人类情绪全景调研.md)；设计与接口合同见 [docs/architecture-contract.md](docs/architecture-contract.md)。

```python
from emotion_os import EmotionEngine, AgentProfile

engine = EmotionEngine(AgentProfile.neurotic_example())
result = engine.process(event, dt_minutes=1.0)   # → 状态 + 中文分级词表 + 4D 维度双通道
```

自然语言入口（v0.2）：注入任意 LLM 调用即可把叙事文本转成事件——

```python
from emotion_os.adapters import NLEventAdapter
adapter = NLEventAdapter(llm_call=my_llm)        # Callable[[str], str]：prompt 进，JSON 出
event = adapter.adapt("反派当众羞辱主角").event   # → Event，经引擎全管线
```

- 领域规则（评价→情绪映射合同）：[docs/grammar/appraisal-grammar.yaml](docs/grammar/appraisal-grammar.yaml)
- 测试：`python -m pytest tests/ -q`（115 项：单元 + 短剧/游戏/音乐等 11 个场景）
- 任务状态：[.tasks/emotion-os-v0.2.task.md](.tasks/emotion-os-v0.2.task.md)（v0.1：[.tasks/emotion-os-v0.1.task.md](.tasks/emotion-os-v0.1.task.md)）

范围：v0.1 为结构化事件输入的研究原型；自然语言适配器与运行时配置见架构合同 §8。

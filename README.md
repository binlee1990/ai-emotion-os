# ai-emotion-os

基于评价理论的「事件 → 评价 → 情绪」可计算情绪引擎（Python 库）。知识基础与理论依据见 [research/人类情绪全景调研.md](research/人类情绪全景调研.md)；设计与接口合同见 [docs/architecture-contract.md](docs/architecture-contract.md)。

```python
from emotion_os import EmotionEngine, AgentProfile

engine = EmotionEngine(AgentProfile.neurotic_example())
result = engine.process(event, dt_minutes=1.0)   # → 状态 + 中文分级词表 + 4D 维度双通道
```

- 领域规则（评价→情绪映射合同）：[docs/grammar/appraisal-grammar.yaml](docs/grammar/appraisal-grammar.yaml)
- 测试：`python -m pytest tests/ -q`
- 任务状态：[.tasks/emotion-os-v0.1.task.md](.tasks/emotion-os-v0.1.task.md)

范围：v0.1 为结构化事件输入的研究原型；自然语言适配器与运行时配置见架构合同 §8。

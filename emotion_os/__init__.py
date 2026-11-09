"""ai-emotion-os：事件 → 评价 → 情绪 → 动力学 → 表达 的可计算情绪引擎。

用法：
    from emotion_os import EmotionEngine, AgentProfile, Event
    engine = EmotionEngine(AgentProfile.reader_example())
    result = engine.process(event, dt_minutes=1.0)

设计合同：docs/architecture-contract.md；知识来源：research/人类情绪全景调研.md。
"""
from .core.agent import AgentProfile
from .core.event import AestheticInfo, BondInfo, Event, MoralInfo, PlayInfo, SocialInfo
from .core.types import EventCategory, Goal, Intent, OCCBranch, Personality
from .engine import EmotionEngine, ProcessResult

__version__ = "0.8.0"   # 与 pyproject.toml 同步

__all__ = [
    "AestheticInfo",
    "AgentProfile",
    "BondInfo",
    "EmotionEngine",
    "Event",
    "EventCategory",
    "Goal",
    "Intent",
    "MoralInfo",
    "OCCBranch",
    "Personality",
    "PlayInfo",
    "ProcessResult",
    "SocialInfo",
]

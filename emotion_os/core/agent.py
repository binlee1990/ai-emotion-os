"""AgentProfile：评价的主体侧输入（调研 §4.2 个体因子 + ALMA 人格层）。"""
from __future__ import annotations

from dataclasses import dataclass, field

from .types import Goal, Personality, StateFactors


@dataclass
class AgentProfile:
    """谁在感受：目标/标准/人格/调节力/共情特质（个体差异，调研 §4.2）。"""

    agent_id: str = "agent"
    goals: dict[str, Goal] = field(default_factory=dict)
    personality: Personality = field(default_factory=Personality)
    state: StateFactors = field(default_factory=StateFactors)

    # 自我理想/道德标准强度（SEC④ 内部标准基线）
    internal_standards: float = 0.5
    # 调节能力（Gross 策略效力乘数；人格参数而非常数，调研 §4.5）
    regulation_capacity: float = 0.5
    # 共情特质（共情疼痛/替代性尴尬强度放大器）
    empathic_trait: float = 0.5
    # 感觉寻求（恐惧享受相关，§4.2 Rozin）
    sensation_seeking: float = 0.5
    # 情绪粒度（词汇分化度→调节能力加成，§4.2）
    emotion_granularity: float = 0.5

    # 对他者的态度 -1–1（fortunes-of-others 方向：喜欢→为他高兴；讨厌→幸灾乐祸）
    liking: dict[str, float] = field(default_factory=dict)
    # 敏感化刺激键（创伤相关线索反应增强，§4.2）
    sensitized_keys: set[str] = field(default_factory=set)

    def goal_importance(self, goal_id: str) -> float:
        g = self.goals.get(goal_id)
        return g.importance if g else 0.0

    def attitude_toward(self, other: str) -> float:
        if other == self.agent_id:
            return 1.0
        return self.liking.get(other, 0.0)

    # ---- 便捷画像 ----
    @staticmethod
    def neurotic_example() -> "AgentProfile":
        """高神经质示例（§4.2：负性易感+强度放大）。"""
        return AgentProfile(
            agent_id="neurotic-example",
            goals={
                "safety": Goal("safety", "人身与财产安全", 0.9),
                "esteem": Goal("esteem", "自尊与地位", 0.7),
            },
            personality=Personality(neuroticism=0.85, extraversion=0.35),
            regulation_capacity=0.35,
            empathic_trait=0.7,
        )

    @staticmethod
    def resilient_example() -> "AgentProfile":
        """低神经质、高调节示例。"""
        return AgentProfile(
            agent_id="resilient-example",
            goals={
                "safety": Goal("safety", "人身与财产安全", 0.7),
                "esteem": Goal("esteem", "自尊与地位", 0.5),
                "craft": Goal("craft", "手艺精进", 0.8),
            },
            personality=Personality(neuroticism=0.2, extraversion=0.6, conscientiousness=0.8),
            regulation_capacity=0.8,
            empathic_trait=0.5,
        )

    @staticmethod
    def reader_example() -> "AgentProfile":
        """短剧/爽文观众示例（§5.4：自我差异、能力感补偿）。"""
        return AgentProfile(
            agent_id="reader-example",
            goals={
                "esteem": Goal("esteem", "自尊与地位", 0.85),
                "justice": Goal("justice", "公平得到伸张", 0.8),
                "bond": Goal("bond", "亲密联结", 0.7),
            },
            personality=Personality(neuroticism=0.6, openness=0.7),
            regulation_capacity=0.45,
            empathic_trait=0.75,
            liking={"villain": -0.9, "hero": 0.8},
        )

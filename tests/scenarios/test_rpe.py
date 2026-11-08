"""场景7：预测误差与惊喜（调研 §1.5.3 RPE：意外之喜 > 预期之喜；剧透改变的是这一层）。"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, Personality


def player() -> AgentProfile:
    return AgentProfile(
        agent_id="player",
        goals={"loot": Goal("loot", "稀有掉落", 0.8)},
        personality=Personality(neuroticism=0.4, extraversion=0.6),
    )


def drop(expectancy_violation: float) -> Event:
    return Event(
        category=EventCategory.ACHIEVEMENT,
        description="出货了",
        goal_impacts={"loot": 0.55},
        expectancy_violation=expectancy_violation,
        novelty=0.3 + 0.6 * expectancy_violation,
        fictionality=0.0, safety_frame=1.0,
    )


def run(ev: float):
    eng = EmotionEngine(player())
    r = eng.process(drop(ev), dt_minutes=1.0)
    return {ep.category: ep.intensity for ep in r.episodes}


class TestRPE:
    def test_unexpected_gain_outranks_expected(self):
        """同一收益：意外 > 预期（多巴胺 RPE）。"""
        expected = run(0.05)
        unexpected = run(0.9)
        joy_e = expected.get("joy", 0) + expected.get("contentment", 0)
        joy_u = unexpected.get("joy", 0) + unexpected.get("contentment", 0)
        assert joy_u > joy_e
        # 惊讶只伴随意外
        assert unexpected.get("surprise", 0) > 0.15
        assert expected.get("surprise", 0) < 0.05

    def test_expectant_gain_leans_contentment(self):
        """预期内的收获偏向满足（低唤醒），意外偏向兴奋。"""
        expected = run(0.05)
        unexpected = run(0.9)
        assert expected.get("contentment", 0) >= expected.get("excitement", 0)
        assert unexpected.get("excitement", 0) >= unexpected.get("contentment", 0)

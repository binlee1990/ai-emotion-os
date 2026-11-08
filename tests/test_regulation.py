"""调节单元测试（N7 出条件）：重评改评价、抑制掩表达留体验付代价（Gross 模型）。"""
from __future__ import annotations

from emotion_os.appraiser import AppraisalEngine
from emotion_os.core import AffectState, AgentProfile, Event, EventCategory, Goal, Intent, Personality
from emotion_os.generation import EmotionGenerator
from emotion_os.regulation import (
    Strategy,
    reinterpret_intent,
    reappraise,
    regulation_strength,
    suppress,
)


def agent(capacity: float = 0.8, granularity: float = 0.7) -> AgentProfile:
    return AgentProfile(
        agent_id="me",
        goals={"esteem": Goal("esteem", importance=0.8)},
        personality=Personality(neuroticism=0.5),
        regulation_capacity=capacity,
        emotion_granularity=granularity,
    )


def insult_event() -> Event:
    return Event(
        category=EventCategory.VIOLATION,
        caused_by="colleague", intent=Intent.DELIBERATE,
        goal_impacts={"esteem": -0.7},
        control_hint=0.7,
    )


class TestReappraisal:
    def test_reappraisal_lowers_negative_generation(self):
        a = agent()
        e = insult_event()
        r = AppraisalEngine().appraise(e, a)
        r2 = reappraise(r, a, Strategy.COGNITIVE_REAPPRAISAL)
        assert r2.goal_relevance < r.goal_relevance
        g1 = EmotionGenerator().generate(r, e, a, AffectState())
        g2 = EmotionGenerator().generate(r2, e, a, AffectState())
        anger1 = {ep.category: ep.intensity for ep in g1.episodes}.get("anger", 0.0)
        anger2 = {ep.category: ep.intensity for ep in g2.episodes}.get("anger", 0.0)
        assert anger2 < anger1

    def test_intent_reinterpretation_defuses_anger(self):
        a = agent()
        r = AppraisalEngine().appraise(insult_event(), a)
        assert r.causality_intent == Intent.DELIBERATE
        r2 = reinterpret_intent(r, a)
        assert r2.causality_intent == Intent.ACCIDENTAL
        e = insult_event()
        g1 = EmotionGenerator().generate(r, e, a, AffectState())
        g2 = EmotionGenerator().generate(r2, e, a, AffectState())
        anger1 = {ep.category: ep.intensity for ep in g1.episodes}.get("anger", 0.0)
        anger2 = {ep.category: ep.intensity for ep in g2.episodes}.get("anger", 0.0)
        assert anger2 < anger1

    def test_weak_regulator_reappraises_less(self):
        weak = agent(capacity=0.1, granularity=0.2)
        strong = agent(capacity=0.9, granularity=0.9)
        r = AppraisalEngine().appraise(insult_event(), strong)
        r_weak = reappraise(r, weak, Strategy.COGNITIVE_REAPPRAISAL)
        r_strong = reappraise(r, strong, Strategy.COGNITIVE_REAPPRAISAL)
        assert r_strong.goal_relevance < r_weak.goal_relevance
        assert regulation_strength(strong) > regulation_strength(weak)

    def test_depleted_state_reduces_reappraisal(self):
        """v0.2：调节力并入状态项——耗竭后重评效力下降（复审 P2-1）。"""
        from emotion_os.core.state import AffectState

        a = agent(capacity=0.8, granularity=0.8)
        fresh = AffectState()
        depleted = AffectState(regulation_depletion=0.9)
        assert regulation_strength(a, depleted) < 0.6 * regulation_strength(a, fresh)
        r = AppraisalEngine().appraise(insult_event(), a)
        r_dep = reappraise(r, a, Strategy.COGNITIVE_REAPPRAISAL, state=depleted)
        r_fresh = reappraise(r, a, Strategy.COGNITIVE_REAPPRAISAL, state=fresh)
        assert r_dep.goal_relevance > r_fresh.goal_relevance   # 耗竭 → 降得更少


class TestSuppression:
    def test_suppression_costs_but_keeps_experience(self):
        state = AffectState(arousal_residue=0.2, regulation_depletion=0.0)
        out = suppress(state, agent())
        assert out.arousal_residue > 0.2          # 生理代价（体验不减、唤醒仍在）
        assert out.regulation_depletion > 0.0     # 调节资源消耗
        # 抑制不触碰情绪层发作（表达层负责掩码）
        assert out.episodes == {}

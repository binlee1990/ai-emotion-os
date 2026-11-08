"""场景5：悬念复合（调研 §4.3：结果不确定×高重要性×临近；Carroll 悖论）。"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, Personality


def fan() -> AgentProfile:
    return AgentProfile(
        agent_id="final-min",
        goals={"safety": Goal("safety", importance=0.9)},
        personality=Personality(neuroticism=0.6),
    )


def match_point(probability: float) -> Event:
    return Event(
        category=EventCategory.THREAT,
        description=f"赛点/炸弹倒计时(p={probability})",
        goal_impacts={"safety": -0.8},
        probability=probability, urgency=0.9, novelty=0.4,
        control_hint=0.2,
        fictionality=1.0, safety_frame=1.0,
    )


def run(probability: float):
    eng = EmotionEngine(fan())
    r = eng.process(match_point(probability), dt_minutes=1.0)
    return {ep.category: ep.intensity for ep in r.episodes}


class TestSuspense:
    def test_peak_at_uncertainty(self):
        """悬而未决(p=0.5)最强；接近确定时让位给具体恐惧/希望。"""
        low = run(0.1); mid = run(0.5); high = run(0.95)
        assert mid.get("suspense", 0) > low.get("suspense", 0)
        assert mid.get("suspense", 0) > high.get("suspense", 0)
        # 悬念=恐惧+希望复合（§3.3）：负向前景中 hope 与恐惧族（未具体化为 fear，先以焦虑在场）并存
        assert mid.get("hope", 0) > 0.1
        assert mid.get("anxiety", 0) > 0.1

    def test_concretization_shifts_to_fear(self):
        """概率→1：不确定变确定，恐惧具体化并超过悬念。"""
        high = run(0.95)
        assert high.get("fear", 0) > high.get("suspense", 0)
        assert high.get("fear", 0) > 0.15

    def test_far_outcome_is_mild(self):
        """概率→0：远端威胁情绪显著弱于悬而未决（相对断言），且无具体恐惧。"""
        far = run(0.05)
        mid = run(0.5)
        assert far.get("suspense", 0) < 0.3 * mid.get("suspense", 1.0)
        assert far.get("fear", 0) < 0.05

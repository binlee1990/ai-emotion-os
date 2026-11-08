"""场景2：恐怖片倒 U（调研 §1.5.4 良性受虐、§5.1 鬼屋实证；grammar R-APP-04）。

享受 = f(恐惧强度) 呈倒 U（峰值在「不能忍受之下一档」）；安全框架破损 → 享受归零。
"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, Personality


def watcher(ss: float = 0.6) -> AgentProfile:
    return AgentProfile(
        agent_id="watcher",
        goals={"safety": Goal("safety", importance=0.9)},
        personality=Personality(neuroticism=0.55, openness=0.7),
        sensation_seeking=ss,
    )


def scare(threat: float, safety: float = 1.0) -> Event:
    return Event(
        category=EventCategory.THREAT,
        description=f"恐怖桥段(threat={threat})",
        goal_impacts={"safety": -threat},
        probability=1.0, urgency=0.8, novelty=0.7,
        control_hint=0.3,
        fictionality=1.0, safety_frame=safety,
    )


def run(threat: float, safety: float = 1.0, ss: float = 0.6):
    eng = EmotionEngine(watcher(ss))
    r = eng.process(scare(threat, safety), dt_minutes=1.0)
    return {ep.category: ep.intensity for ep in r.episodes}


class TestInvertedU:
    def test_enjoyment_inverted_u_and_frame_break(self):
        """R-APP-04：低/中/高三档 → 中档享受最高；破框架 → 享受归零且恐惧主导。"""
        low = run(0.30)
        mid = run(0.60)
        high = run(0.95)

        fe_low, fe_mid, fe_high = low.get("fear_enjoyment", 0), mid.get("fear_enjoyment", 0), high.get("fear_enjoyment", 0)
        # 倒 U：中档 > 低档 且 中档 > 高档
        assert fe_mid > fe_low, f"mid={fe_mid} low={fe_low}"
        assert fe_mid > fe_high, f"mid={fe_mid} high={fe_high}"
        # 恐惧本身单调上升
        assert high.get("fear", 0) > mid.get("fear", 0) > low.get("fear", 0)

        # 安全框架破损（影院着火）：享受归零，纯恐惧主导
        broke = run(0.95, safety=0.0)
        assert broke.get("fear_enjoyment", 0) == 0.0
        assert broke.get("fear", 0) > 0.2

    def test_sensation_seeking_amplifies_fear_enjoyment(self):
        """§4.2：感觉寻求与恐惧享受强相关。"""
        low_ss = run(0.6, ss=0.1).get("fear_enjoyment", 0)
        high_ss = run(0.6, ss=0.95).get("fear_enjoyment", 0)
        assert high_ss > low_ss

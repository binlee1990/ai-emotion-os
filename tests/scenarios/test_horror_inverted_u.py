"""场景2：恐怖片倒 U（调研 §1.5.4 良性受虐、§5.1 鬼屋实证；grammar R-APP-04）。

享受 = f(恐惧强度) 呈倒 U；顶点 FEAR_ENJOYMENT_PEAK=0.84 出自 Andersen et al. 2020
OSF 开放数据复现拟合（Likert 7.55/9 换算，scripts/fit_fear_enjoyment_peak.py）。
安全框架破损 → 享受归零。
"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, Personality
from emotion_os.generation.mapping import FEAR_ENJOYMENT_PEAK, _tent


def watcher(ss: float = 0.6) -> AgentProfile:
    return AgentProfile(
        agent_id="watcher",
        goals={"safety": Goal("safety", importance=0.9)},
        personality=Personality(neuroticism=0.55, openness=0.7),
        sensation_seeking=ss,
    )


def scare(threat: float, safety: float = 1.0, urgency: float = 1.0, novelty: float = 1.0) -> Event:
    return Event(
        category=EventCategory.THREAT,
        description=f"恐怖桥段(threat={threat})",
        goal_impacts={"safety": -threat},
        probability=1.0, urgency=urgency, novelty=novelty,
        control_hint=0.0,  # 观众对银幕威胁零控制
        fictionality=1.0, safety_frame=safety,
    )


def run(threat: float, safety: float = 1.0, ss: float = 0.6):
    eng = EmotionEngine(watcher(ss))
    r = eng.process(scare(threat, safety), dt_minutes=1.0)
    return {ep.category: ep.intensity for ep in r.episodes}


class TestInvertedU:
    def test_enjoyment_inverted_u_and_frame_break(self):
        """R-APP-04：低/峰/高三档（urgency=novelty=1 使 fear 激活覆盖顶点两侧）
        → 峰档享受最高；破框架 → 享受归零且恐惧主导。"""
        low = run(0.5)
        peak = run(0.9)
        high = run(1.0)

        fe_low, fe_peak, fe_high = (
            low.get("fear_enjoyment", 0), peak.get("fear_enjoyment", 0), high.get("fear_enjoyment", 0)
        )
        # 倒 U：峰档 > 低档 且 峰档 > 高档（下降段可达，因顶点 0.84 在 fear 激活范围内）
        assert fe_peak > fe_low, f"peak={fe_peak} low={fe_low}"
        assert fe_peak > fe_high, f"peak={fe_peak} high={fe_high}"
        # 恐惧本身随威胁上升（高档双双饱和到 1.0，比较未饱和段）
        assert low.get("fear", 0) < peak.get("fear", 0)
        assert high.get("fear", 0) >= peak.get("fear", 0) > 0.8

        # 安全框架破损（影院着火）：享受归零，纯恐惧主导
        broke = run(1.0, safety=0.0)
        assert broke.get("fear_enjoyment", 0) == 0.0
        assert broke.get("fear", 0) > 0.2

    def test_peak_position_pinned_to_calibration(self):
        """v0.3：钉住常数与拟合值一致（7.55/9 → 0.84，防止常数漂移；经验效力在
        scripts/fit_fear_enjoyment_peak.py 复跑，非本测试），并检验 tent 形状：
        顶点处最大、两侧下降；极高恐惧（>0.9）享受不足峰值的 40%。"""
        assert FEAR_ENJOYMENT_PEAK == 0.84
        assert _tent(FEAR_ENJOYMENT_PEAK, FEAR_ENJOYMENT_PEAK) == 1.0
        assert _tent(0.5, FEAR_ENJOYMENT_PEAK) < _tent(0.8, FEAR_ENJOYMENT_PEAK) < 1.0
        assert _tent(0.95, FEAR_ENJOYMENT_PEAK) < 0.4

    def test_sensation_seeking_amplifies_fear_enjoyment(self):
        """§4.2：感觉寻求与恐惧享受强相关。"""
        low_ss = run(0.9, ss=0.1).get("fear_enjoyment", 0)
        high_ss = run(0.9, ss=0.95).get("fear_enjoyment", 0)
        assert high_ss > low_ss

    def test_safety_frame_smooth_ramp(self):
        """v0.2：安全框架平滑过渡（0.2–0.8 线性坡）——半安全给半享受，无悬崖。"""
        full = run(0.9, safety=1.0).get("fear_enjoyment", 0)
        half = run(0.9, safety=0.5).get("fear_enjoyment", 0)
        zero = run(0.9, safety=0.0).get("fear_enjoyment", 0)
        assert zero == 0.0
        assert full > 0.1
        # 坡中点 sf=0.5 → sf_ramp=(0.5-0.2)/0.6=0.5：享受约为全安全的一半
        assert 0.4 * full < half < 0.6 * full

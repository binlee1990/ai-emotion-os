"""核心域模型单元测试（N4 出条件；架构合同 §4.3 数据结构）。"""
from __future__ import annotations

import math

import pytest

from emotion_os.core import (
    AffectState,
    AgentProfile,
    BondInfo,
    EmotionEpisode,
    Event,
    EventCategory,
    Goal,
    Intent,
    MemoryTrace,
    MoodState,
    SocialInfo,
)


class TestEventSchema:
    def test_event_minimal(self):
        e = Event(category=EventCategory.LOSS)
        assert e.affects == "self"
        assert e.intent == Intent.UNKNOWN
        assert e.safety_frame == 1.0

    def test_structured_infos(self):
        e = Event(
            category=EventCategory.BOND,
            bond=BondInfo(delta=0.8, sudden=True),
            social=SocialInfo(direction="up", deservedness=0.9),
        )
        assert e.bond.sudden and e.social.deservedness == 0.9

    def test_event_is_frozen(self):
        e = Event(category=EventCategory.THREAT)
        with pytest.raises(Exception):
            e.urgency = 0.9  # type: ignore[misc]


class TestAgentProfile:
    def test_goal_importance_missing_goal(self):
        a = AgentProfile(goals={"x": Goal("x", importance=0.8)})
        assert a.goal_importance("x") == 0.8
        assert a.goal_importance("nope") == 0.0

    def test_attitude_toward_self_and_others(self):
        a = AgentProfile(agent_id="me", liking={"foe": -0.8})
        assert a.attitude_toward("me") == 1.0
        assert a.attitude_toward("foe") == -0.8
        assert a.attitude_toward("stranger") == 0.0

    def test_reader_example_has_disposition_keys(self):
        a = AgentProfile.reader_example()
        assert a.attitude_toward("villain") < 0 < a.attitude_toward("hero")


class TestAffectState:
    def test_episode_decay_exponential(self):
        ep = EmotionEpisode(category="anger", intensity=0.8, onset_min=0.0, half_life_min=12.0)
        state = AffectState(now_min=12.0, episodes={"anger": ep})
        assert math.isclose(state.activation("anger"), 0.4, rel_tol=1e-9)

    def test_activation_absent_category_zero(self):
        assert AffectState().activation("joy") == 0.0

    def test_mood_slow_ema(self):
        m = MoodState(valence=0.0)
        m.update(valence=-1.0, arousal=0.9, weight=0.05)  # 单事件只微移
        assert -0.06 < m.valence < -0.04

    def test_memory_peak_end_and_duration_neglect(self):
        mem = MemoryTrace()
        for _ in range(10):            # 时长（事件数）不进入公式
            mem.observe(valence=0.3, intensity=0.4)
        assert mem.events == 10
        assert math.isclose(mem.remembered_valence, 0.3, abs_tol=1e-9)  # 峰=终=0.3
        mem.observe(valence=-0.8, intensity=0.7)   # 坏结局成为强度峰
        # 峰=-0.8（强度 0.7>0.4 夺峰），终=-0.8 → 记忆评分 = -0.8
        assert math.isclose(mem.remembered_valence, -0.8)
        mem2 = MemoryTrace()
        for _ in range(3):             # 同型短体验（时长缩短）评分不变：时长忽视
            mem2.observe(valence=0.3, intensity=0.4)
        assert math.isclose(mem2.remembered_valence, 0.3, abs_tol=1e-9)

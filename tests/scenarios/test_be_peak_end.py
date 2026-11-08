"""场景4：BE 结局与意难平（调研 §1.5.10 峰终定律、§3.3 意难平、§5.1 BE 行）。"""
from __future__ import annotations

from emotion_os import AgentProfile, BondInfo, EmotionEngine, Event, EventCategory, Goal


def drama_fan() -> AgentProfile:
    return AgentProfile(
        agent_id="drama-fan",
        goals={"bond": Goal("bond", "与角色的情感联结", 0.85)},
        empathic_trait=0.8,
    )


def high_moment() -> Event:
    return Event(
        category=EventCategory.BOND,
        description="高光：主角团劫后重逢",
        bond=BondInfo(delta=0.85, sudden=True),
        fictionality=1.0, safety_frame=1.0,
    )


def ending(be: bool) -> Event:
    return Event(
        category=EventCategory.LOSS,
        description="BE：挚爱角色牺牲" if be else "HE：圆满收尾",
        goal_impacts={"bond": -0.95 if be else 0.0},
        reversibility=0.0 if be else 1.0,
        pleasantness=0.0 if be else 0.7,
        fictionality=1.0, safety_frame=1.0,
    )


def watch(n_high: int, be: bool):
    eng = EmotionEngine(drama_fan())
    for _ in range(n_high):
        eng.process(high_moment(), dt_minutes=10.0)
    eng.process(ending(be), dt_minutes=5.0)
    return eng


class TestBEEnding:
    def test_be_worse_remembered_than_he(self):
        be = watch(2, be=True)
        he = watch(2, be=False)
        assert be.state.memory.remembered_valence < he.state.memory.remembered_valence - 0.3

    def test_duration_neglect_at_story_level(self):
        """同结局、时长翻倍 → 记忆评分几乎不变（峰终定律的时长忽视）。"""
        short_be = watch(1, be=True)
        long_be = watch(4, be=True)
        assert abs(short_be.state.memory.remembered_valence - long_be.state.memory.remembered_valence) < 0.15

    def test_be_yields_yinanping_rumination(self):
        eng = watch(2, be=True)
        # 不可逆高重要性损失 → 反刍压力与意难平
        assert eng.state.rumination > 0.2
        r = eng.process(
            Event(category=EventCategory.NOVELTY, novelty=0.5, description="回想结局"),
            dt_minutes=30.0,
        )
        a = {ep.category: ep.intensity for ep in r.episodes}
        assert a.get("yi_nan_ping", 0) > 0.1

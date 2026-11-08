"""场景扩展：§6.2 主对照表剩余行——后悔/无聊/敬畏/惊吓/顿悟。"""
from __future__ import annotations

from emotion_os import AestheticInfo, AgentProfile, EmotionEngine, Event, EventCategory, Goal, Personality
from emotion_os.core.types import TimeOrientation


def matrix_agent() -> AgentProfile:
    return AgentProfile(
        agent_id="matrix",
        goals={"wealth": Goal("wealth", 0.7), "attention": Goal("attention", "注意力资源", 0.6)},
        personality=Personality(neuroticism=0.5, openness=0.8),
    )


def acts(result):
    return {ep.category: ep.intensity for ep in result.episodes}


class TestMatrixRows:
    def test_regret_on_reversible_past_self_caused_loss(self):
        """回忆-负性：过去+自因+可逆损失 → 后悔（反事实自责）。"""
        e = Event(
            category=EventCategory.LOSS, description="想起当年卖飞的股票", affects="self",
            caused_by="matrix", goal_impacts={"wealth": -0.5},
            reversibility=0.6, time_orientation=TimeOrientation.PAST,
        )
        a = acts(EmotionEngine(matrix_agent()).process(e, dt_minutes=1.0))
        assert a.get("regret", 0) > 0.1

    def test_boredom_on_value_depletion(self):
        """信息枯竭：注意被占用但无信息价值 → 无聊（§3.3 Pekrun）。"""
        e = Event(
            category=EventCategory.NOVELTY, description="注水剧情第 8 集", affects="self",
            goal_impacts={"attention": 0.06},  # 注意被占用但几乎无促进/阻碍 → 价值枯竭
            novelty=0.05, pleasantness=0.0,
        )
        a = acts(EmotionEngine(matrix_agent()).process(e, dt_minutes=1.0))
        assert a.get("boredom", 0) > 0.1

    def test_awe_on_vastness(self):
        """巨大/超常对象 → 敬畏（vastness+accommodation）。"""
        e = Event(
            category=EventCategory.AESTHETIC, description="深夜看见银河", affects="self",
            aesthetic=AestheticInfo(vastness=0.9), novelty=0.3,
        )
        a = acts(EmotionEngine(matrix_agent()).process(e, dt_minutes=1.0))
        assert a.get("awe", 0) > 0.2

    def test_startle_on_sudden_threat(self):
        """即时危险：突发+高紧迫 → 惊吓（脑干级）。"""
        e = Event(
            category=EventCategory.THREAT, description="衣柜里窜出黑影", affects="self",
            goal_impacts={"attention": -0.4},
            novelty=0.95, urgency=0.9, probability=1.0, control_hint=0.3,
        )
        a = acts(EmotionEngine(matrix_agent()).process(e, dt_minutes=0.5))
        assert a.get("startle", 0) > 0.2

    def test_aha_on_insight(self):
        """理解发生：缺口闭合 → 顿悟。"""
        e = Event(
            category=EventCategory.NOVELTY, description="伏笔全线贯通", affects="self",
            goal_impacts={"attention": 0.3}, novelty=0.6, insight=True,
        )
        a = acts(EmotionEngine(matrix_agent()).process(e, dt_minutes=1.0))
        assert a.get("aha", 0) > 0.4

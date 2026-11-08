"""场景扩展：音乐（调研 §5.5 BRECVEMA 可事件化子集；Juslin & Västfjäll 2008）。

悲伤音乐悖论（Taruffi & Koelsch 2014：怀旧 76% > 悲伤 44.9%）；预期解决 chills；节奏活力。
"""
from __future__ import annotations

from emotion_os import AestheticInfo, AgentProfile, EmotionEngine, Event, EventCategory, Goal, Personality


def listener() -> AgentProfile:
    return AgentProfile(
        agent_id="listener",
        goals={"performance": Goal("performance", "在意演出质量", 0.6)},
        personality=Personality(neuroticism=0.4, openness=0.85),
        empathic_trait=0.7,
    )


def acts(result):
    return {ep.category: ep.intensity for ep in result.episodes}


class TestSadMusicParadox:
    def test_sad_song_elicits_nostalgia_not_sadness(self):
        """悲伤音乐悖论：最常诱发的是怀旧而非悲伤（§5.5）。
        pleasantness 取轻度正值=「享受的悲伤」净体验（无现实后果奖赏+情绪调节奖赏）。"""
        from emotion_os.core.types import TimeOrientation
        e = Event(
            category=EventCategory.AESTHETIC,
            description="老歌前奏响起", affects="self",
            aesthetic=AestheticInfo(beauty=0.6),
            pleasantness=0.3, time_orientation=TimeOrientation.PAST,
        )
        a = acts(EmotionEngine(listener()).process(e, dt_minutes=1.0))
        assert a.get("nostalgia", 0) > 0.05
        # Taruffi & Koelsch 2014：怀旧 76% > 悲伤 44.9%——悲伤可共存但以怀旧为主；
        # 本操作化下无目标丧失故悲伤≈0（比调研更弱一侧，方向一致）
        sadness_total = sum(v for k, v in a.items() if k in ("sadness", "grief", "despair", "heartbreak"))
        assert sadness_total <= 0.2 * a.get("nostalgia", 1e-6)


class TestChills:
    def test_expectation_resolution_yields_chills(self):
        """音乐预期（M 机制）：张力积累→解决处产生 chills（§5.5；Blood & Zatorre 2001）。"""
        eng = EmotionEngine(listener())
        buildup = Event(
            category=EventCategory.THREAT,
            description="渐强的不和谐张力", affects="self",
            goal_impacts={"performance": -0.3},
            probability=0.6, urgency=0.7, novelty=0.4, control_hint=0.2,
        )
        eng.process(buildup, dt_minutes=1.0)
        assert eng.state.activation("suspense") > 0.05    # 张力在场
        resolve = Event(
            category=EventCategory.AESTHETIC,
            description="解决和弦回归主调", affects="self",
            aesthetic=AestheticInfo(beauty=0.9),
            pleasantness=0.6, prior_threat_resolved=True,
        )
        a = acts(eng.process(resolve, dt_minutes=1.0))
        assert a.get("chills", 0) > 0.1
        # 对照：无前置张力时同段解决不产生 chills
        a_cold = acts(EmotionEngine(listener()).process(resolve, dt_minutes=1.0))
        assert a_cold.get("chills", 0) < a.get("chills", 0)


class TestEntrainment:
    def test_rhythm_raises_vitality(self):
        """节奏夹带（R 机制）：节拍驱动的身体活力。"""
        e = Event(
            category=EventCategory.BODY,
            description="副歌鼓点全场蹦跳", affects="self",
            pleasantness=0.6, novelty=0.3,
        )
        a = acts(EmotionEngine(listener()).process(e, dt_minutes=1.0))
        assert a.get("vitality", 0) > 0.1

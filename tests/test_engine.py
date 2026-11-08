"""引擎组装测试（N8 出条件）：管线贯通、调节策略接入、习惯化接入。"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, Intent, MoralInfo
from emotion_os.regulation import Strategy


def engine() -> EmotionEngine:
    return EmotionEngine(AgentProfile.reader_example())


def humiliation() -> Event:
    return Event(
        category=EventCategory.VIOLATION,
        caused_by="villain", intent=Intent.DELIBERATE,
        goal_impacts={"esteem": -0.6},
        moral=MoralInfo(severity=0.6, victim="hero", violator="villain"),
        control_hint=0.3,           # 主角暂时无力反抗 → 憋屈
        description="反派当众羞辱主角",
    )


class TestPipeline:
    def test_process_returns_all_channels(self):
        eng = engine()
        r = eng.process(humiliation(), dt_minutes=1.0)
        assert r.appraisal.goal_relevance > 0.3
        assert r.episodes, "应产生情绪发作"
        assert r.expression.entries and r.expression.dims is not None
        zh_words = [e.word for e in r.expression.entries]
        assert all(w for w in zh_words)

    def test_reappraisal_strategy_lowers_anger_via_engine(self):
        e1 = EmotionEngine(AgentProfile.reader_example())
        e2 = EmotionEngine(AgentProfile.reader_example())
        r1 = e1.process(humiliation())
        r2 = e2.process(humiliation(), strategy=Strategy.COGNITIVE_REAPPRAISAL)
        a1 = {ep.category: ep.intensity for ep in r1.episodes}.get("anger", 0.0)
        a2 = {ep.category: ep.intensity for ep in r2.episodes}.get("anger", 0.0)
        assert a2 < a1

    def test_suppression_masks_expression_not_experience(self):
        e1 = EmotionEngine(AgentProfile.reader_example())
        e2 = EmotionEngine(AgentProfile.reader_example())
        r1 = e1.process(humiliation())
        r2 = e2.process(humiliation(), strategy=Strategy.RESPONSE_SUPPRESSION)
        assert r2.expression.suppressed and not r1.expression.suppressed
        # 体验不减：发作类别集合一致
        assert {ep.category for ep in r2.episodes} == {ep.category for ep in r1.episodes}
        # 代价：唤醒残余更高
        assert e2.state.arousal_residue >= e1.state.arousal_residue

    def test_habituation_applies_via_stimulus_key(self):
        eng = engine()
        ev = Event(category=EventCategory.NOVELTY, novelty=0.8, stimulus_key="meme-42",
                   pleasantness=0.3)
        r1 = eng.process(ev, dt_minutes=0.1)
        r2 = eng.process(ev, dt_minutes=0.1)
        s1 = {ep.category: ep.intensity for ep in r1.episodes}.get("curiosity", 0.0)
        s2 = {ep.category: ep.intensity for ep in r2.episodes}.get("curiosity", 0.0)
        assert r2.habituation_multiplier < 1.0
        assert s2 < s1

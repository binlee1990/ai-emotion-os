"""场景3：重逢与 kama muta（调研 §1.5.8 Zickfeld 2018；grammar R-APP-05 人工合同的场景测试）。

骤增触发被感动（短时程）；渐进增强只产生温情，不触发。
"""
from __future__ import annotations

from emotion_os import AgentProfile, BondInfo, EmotionEngine, Event, EventCategory, Goal


def bonded_reader() -> AgentProfile:
    return AgentProfile(
        agent_id="reunion-watcher",
        goals={"bond": Goal("bond", "亲密联结", 0.8)},
        empathic_trait=0.75,
    )


def reunion(sudden: bool) -> Event:
    return Event(
        category=EventCategory.BOND,
        description="失散多年母女重逢" if sudden else "关系逐日回暖",
        bond=BondInfo(delta=0.9, sudden=sudden),
        fictionality=1.0, safety_frame=1.0,
    )


def acts(result):
    return {ep.category: ep.intensity for ep in result.episodes}


class TestKamaMuta:
    def test_sudden_reunion_triggers_kama_muta_short_course(self):
        eng = EmotionEngine(bonded_reader())
        r = eng.process(reunion(sudden=True), dt_minutes=0.5)
        a = acts(r)
        assert a.get("kama_muta", 0) > 0.3
        peak = eng.state.activation("kama_muta")
        # 时程 1–2 分钟：3 分钟后衰减过半以上（半衰期 1.5 分钟）
        eng.dynamics.tick(eng.state, 3.0)
        assert eng.state.activation("kama_muta") < 0.5 * peak

    def test_gradual_warmth_no_kama_muta(self):
        """R-APP-05：渐进增强 → 温情而非感动。"""
        eng_sudden = EmotionEngine(bonded_reader())
        eng_gradual = EmotionEngine(bonded_reader())
        a_sudden = acts(eng_sudden.process(reunion(sudden=True), dt_minutes=0.5))
        a_gradual = acts(eng_gradual.process(reunion(sudden=False), dt_minutes=0.5))
        assert a_gradual.get("kama_muta", 0) < 0.35 * a_sudden.get("kama_muta", 1.0)
        assert a_gradual.get("tenderness", 0) > a_gradual.get("kama_muta", 0)

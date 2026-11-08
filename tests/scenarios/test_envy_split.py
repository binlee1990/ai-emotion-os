"""场景6：羡慕分流（调研 §3.3 van de Ven 2009/2011/2015；grammar R-APP-03 人工合同的场景测试）。

上行比较 × 应得感 → 良性（上进）vs 恶意（拉倒+后续幸灾乐祸）。
"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, SocialInfo


def office_worker() -> AgentProfile:
    a = AgentProfile(
        agent_id="office",
        goals={"esteem": Goal("esteem", "职级与认可", 0.8)},
        empathic_trait=0.5,
    )
    a.liking = {"merit_peer": 0.2, "nepotism_peer": -0.4}
    return a


def promotion(direction_target: str, deservedness: float) -> Event:
    return Event(
        category=EventCategory.COMPARISON,
        description=f"{direction_target} 升职(应得感={deservedness})",
        affects=direction_target,
        social=SocialInfo(direction="up", deservedness=deservedness),
    )


def exposure(target: str, deservedness_of_fall: float) -> Event:
    """对方跌落（舞弊被曝光等）。"""
    return Event(
        category=EventCategory.COMPARISON,
        description=f"{target} 跌落",
        affects=target,
        social=SocialInfo(direction="down", deservedness=deservedness_of_fall),
    )


def run(seq):
    eng = EmotionEngine(office_worker())
    results = [eng.process(e, dt_minutes=1.0) for e in seq]
    return eng, [{ep.category: ep.intensity for ep in r.episodes} for r in results]


class TestEnvySplit:
    def test_merit_promotion_benign(self):
        _, acts = run([promotion("merit_peer", 0.9)])
        a = acts[0]
        assert a.get("benign_envy", 0) > a.get("malicious_envy", 0)
        assert a.get("benign_envy", 0) > 0.1

    def test_nepotism_promotion_malicious(self):
        _, acts = run([promotion("nepotism_peer", 0.1)])
        a = acts[0]
        assert a.get("malicious_envy", 0) > a.get("benign_envy", 0)
        assert a.get("malicious_envy", 0) > 0.1

    def test_malicious_envy_predicts_schadenfreude(self):
        """van de Ven 2015：恶意羡慕者的后续幸灾乐祸更强（跨事件因果：前置羡慕改变输出）。"""
        _, acts_mal = run([promotion("nepotism_peer", 0.1), exposure("nepotism_peer", 0.8)])
        _, acts_no_prior = run([exposure("nepotism_peer", 0.8)])   # 无前置羡慕的对照臂
        _, acts_ben = run([promotion("merit_peer", 0.9), exposure("merit_peer", 0.3)])
        sch_mal = acts_mal[1].get("schadenfreude", 0)
        sch_no_prior = acts_no_prior[0].get("schadenfreude", 0)
        sch_ben = acts_ben[1].get("schadenfreude", 0)
        assert sch_no_prior > 0.03            # 好恶+应得感基线
        assert sch_mal > sch_no_prior         # 先前恶意羡慕提升（跨事件链生效）
        assert sch_mal > sch_ben

"""情绪生成单元测试（N6 出条件）：类别目录、家族映射、4D 混合。"""
from __future__ import annotations

from emotion_os.appraiser import AppraisalEngine
from emotion_os.core import AffectState, AgentProfile, Event, EventCategory, Goal, Intent, MoralInfo, SocialInfo
from emotion_os.generation import EmotionGenerator
from emotion_os.generation.catalog import CATALOG, FAMILY_OF
from emotion_os.generation.dimensions import blend


def agent() -> AgentProfile:
    a = AgentProfile(
        agent_id="me",
        goals={
            "safety": Goal("safety", importance=0.9),
            "esteem": Goal("esteem", importance=0.8),
            "justice": Goal("justice", importance=0.8),
        },
        empathic_trait=0.7,
    )
    a.liking = {"villain": -0.9, "hero": 0.8, "friend": 0.8}
    return a


def gen(e: Event, a: AgentProfile | None = None, state: AffectState | None = None):
    a = a or agent()
    r = AppraisalEngine().appraise(e, a)
    return EmotionGenerator().generate(r, e, a, state or AffectState()), r


class TestCatalog:
    def test_catalog_size_and_families(self):
        assert len(CATALOG) >= 50
        assert set(FAMILY_OF.values()) >= {
            "anger", "fear", "disgust", "sadness", "joy",
            "self_conscious", "social_moral", "love", "epistemic", "aesthetic", "prospect",
        }

    def test_chinese_specific_words_present(self):
        for w in ("wei_yuan", "jie_qi", "shuang", "bie_qu", "xin_teng", "yi_nan_ping", "po_fang", "ke_dao", "numb"):
            assert w in CATALOG and CATALOG[w].zh


class TestFamilyMapping:
    def test_deliberate_obstruction_high_control_yields_anger(self):
        e = Event(
            category=EventCategory.VIOLATION,
            caused_by="colleague", intent=Intent.DELIBERATE,
            goal_impacts={"esteem": -0.7},
            control_hint=0.7,
        )
        g, _ = gen(e)
        acts = {ep.category: ep.intensity for ep in g.episodes}
        assert acts.get("anger", 0) > 0.25

    def test_low_control_threat_yields_anxiety_not_anger(self):
        """R-APP-01 反例：低控制+不确定 → 焦虑而非愤怒。"""
        e = Event(
            category=EventCategory.THREAT,
            goal_impacts={"safety": -0.7}, probability=0.5,
            urgency=0.6, control_hint=0.1,
        )
        g, _ = gen(e)
        acts = {ep.category: ep.intensity for ep in g.episodes}
        assert acts.get("anxiety", 0) > 0.15
        assert acts.get("anger", 0) < acts.get("anxiety", 0)

    def test_irreversible_loss_yields_sadness_grief(self):
        e = Event(category=EventCategory.LOSS, goal_impacts={"safety": -0.9}, reversibility=0.0)
        g, _ = gen(e)
        acts = {ep.category: ep.intensity for ep in g.episodes}
        assert acts.get("sadness", 0) > 0.3
        assert acts.get("grief", 0) > 0.15

    def test_virtue_witness_yields_elevation(self):
        e = Event(
            category=EventCategory.VIOLATION,
            moral=MoralInfo(severity=0.9, virtue=True, victim="none"),
        )
        g, _ = gen(e)
        acts = {ep.category: ep.intensity for ep in g.episodes}
        assert acts.get("elevation", 0) > 0.2

    def test_sudden_bond_yields_kama_muta_gradual_does_not(self):
        from emotion_os.core import BondInfo
        es = Event(category=EventCategory.BOND, bond=BondInfo(delta=0.85, sudden=True))
        eg = Event(category=EventCategory.BOND, bond=BondInfo(delta=0.85, sudden=False))
        gs, _ = gen(es)
        gg, _ = gen(eg)
        a_sudden = {ep.category: ep.intensity for ep in gs.episodes}.get("kama_muta", 0)
        a_gradual = {ep.category: ep.intensity for ep in gg.episodes}.get("kama_muta", 0)
        assert a_sudden > 0.3
        assert a_gradual < 0.35 * a_sudden  # 渐进不触发（R-APP-05）


class TestDimsBlending:
    def test_blend_mixed_states(self):
        d = blend({"anger": 0.6, "amusement": 0.6})
        assert -0.1 < d.valence < 0.1          # 又好气又好笑：效价近中
        assert d.arousal > 0.5
        assert blend({}).valence == 0.0

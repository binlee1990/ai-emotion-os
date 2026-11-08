"""评价器单元测试（N5 出条件）：SEC 维度计算 + OCC 分支 + 低控制分流反例的评价底座。"""
from __future__ import annotations

from emotion_os.appraiser import AppraisalEngine
from emotion_os.core import AgentProfile, Event, EventCategory, Goal, Intent, MoralInfo, Personality, SocialInfo
from emotion_os.core.types import OCCBranch


def base_agent() -> AgentProfile:
    agent = AgentProfile(
        agent_id="me",
        goals={
            "safety": Goal("safety", importance=0.9),
            "esteem": Goal("esteem", importance=0.7),
            "justice": Goal("justice", importance=0.8),
        },
        empathic_trait=0.6,
    )
    agent.liking = {"friend": 0.8, "foe": -0.8, "villain": -0.9}
    return agent


class TestSECRelevance:
    def test_goal_relevance_from_touched_goals(self):
        e = Event(category=EventCategory.THREAT, goal_impacts={"safety": -0.8})
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.goal_relevance == 0.9

    def test_zero_relevance_for_irrelevant_event(self):
        """G2 反例-1：无目标关联的葬礼 → 相关性≈0（下游一切激活为零）。"""
        agent = AgentProfile(goals={"craft": Goal("craft", importance=0.8)})
        e = Event(category=EventCategory.LOSS, description="陌生人的远亲葬礼")
        r = AppraisalEngine().appraise(e, agent)
        assert r.goal_relevance <= 0.05

    def test_other_affect_relevance_via_empathy(self):
        e = Event(category=EventCategory.LOSS, affects="stranger")
        r = AppraisalEngine().appraise(e, base_agent())
        assert 0.0 < r.goal_relevance < 0.6  # 经共情传导但弱于自身目标

    def test_moral_witness_relevance_via_justice_goal(self):
        e = Event(
            category=EventCategory.VIOLATION,
            moral=MoralInfo(severity=0.8, victim="student", violator="cheater"),
        )
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.goal_relevance >= 0.5


class TestSECImplicationsAndCoping:
    def test_conduciveness_importance_weighted(self):
        agent = base_agent()
        e = Event(
            category=EventCategory.ACHIEVEMENT,
            goal_impacts={"safety": 0.2, "esteem": 0.8},  # 安全 0.9、自尊 0.7
        )
        r = AppraisalEngine().appraise(e, agent)
        expected = (0.2 * 0.9 + 0.8 * 0.7) / (0.9 + 0.7)
        assert abs(r.conduciveness - expected) < 1e-9

    def test_attribution_self_normalized(self):
        e = Event(category=EventCategory.ACHIEVEMENT, caused_by="me", goal_impacts={"esteem": 0.6})
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.causality_agent == "self" and r.self_caused

    def test_deliberate_other_flag(self):
        e = Event(
            category=EventCategory.VIOLATION,
            caused_by="colleague",
            intent=Intent.DELIBERATE,
            goal_impacts={"esteem": -0.7},
        )
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.deliberate_other

    def test_low_control_hint_preserved(self):
        """R-APP-01 反例底座：待复查报告（低控制+不确定）→ 评价配置指向焦虑而非愤怒。"""
        e = Event(
            category=EventCategory.THREAT,
            goal_impacts={"safety": -0.7},
            probability=0.5,
            urgency=0.6,
            control_hint=0.1,
        )
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.control == 0.1
        assert r.threat_level > 0.25
        assert not r.deliberate_other
        assert OCCBranch.PROSPECTS in r.occ_branches

    def test_neurotic_agent_lower_power(self):
        calm = base_agent()  # neuroticism 默认 0.5
        anxious = AgentProfile(
            agent_id="me",
            goals={"safety": Goal("safety", importance=0.9)},
            personality=Personality(neuroticism=0.95),
        )
        e = Event(category=EventCategory.THREAT, goal_impacts={"safety": -0.7})
        eng = AppraisalEngine()
        assert eng.appraise(e, anxious).power < eng.appraise(e, calm).power


class TestSECNormativeAndBranches:
    def test_self_caused_violation_internal_negative(self):
        e = Event(
            category=EventCategory.VIOLATION,
            caused_by="me",
            intent=Intent.DELIBERATE,
            moral=MoralInfo(severity=0.7, victim="friend", violator="me"),
        )
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.internal_standard < -0.5
        assert OCCBranch.AGENCY_SELF in r.occ_branches

    def test_other_violation_external_negative(self):
        e = Event(
            category=EventCategory.VIOLATION,
            caused_by="villain",
            moral=MoralInfo(severity=0.8, victim="me", violator="villain"),
        )
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.external_standard < -0.5
        assert OCCBranch.AGENCY_OTHER in r.occ_branches

    def test_virtue_witness_positive_external(self):
        e = Event(
            category=EventCategory.VIOLATION,
            moral=MoralInfo(severity=0.9, virtue=True, victim="none"),
        )
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.external_standard > 0.5

    def test_primary_branch_priority(self):
        # 社会比较特异性最高
        e = Event(category=EventCategory.COMPARISON, social=SocialInfo(direction="up", deservedness=0.2))
        r = AppraisalEngine().appraise(e, base_agent())
        assert r.primary_branch == OCCBranch.SOCIAL_COMPARISON
        # 纯前景事件
        e2 = Event(category=EventCategory.THREAT, goal_impacts={"safety": -0.6}, probability=0.4)
        assert AppraisalEngine().appraise(e2, base_agent()).primary_branch == OCCBranch.PROSPECTS
        # 普通后果事件
        e3 = Event(category=EventCategory.ACHIEVEMENT, goal_impacts={"esteem": 0.6})
        assert AppraisalEngine().appraise(e3, base_agent()).primary_branch == OCCBranch.CONSEQUENCES

    def test_threat_level_scales_with_probability(self):
        eng = AppraisalEngine()
        base = dict(goal_impacts={"safety": -0.8}, urgency=0.7)
        low = eng.appraise(Event(category=EventCategory.THREAT, probability=0.3, **base), base_agent())
        high = eng.appraise(Event(category=EventCategory.THREAT, probability=1.0, **base), base_agent())
        assert high.threat_level > low.threat_level

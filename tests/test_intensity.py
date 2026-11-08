"""强度模型单元测试（N6 出条件；承载 grammar R-INT-01 / R-INT-02 的 formal 声明）。"""
from __future__ import annotations

from emotion_os.appraiser import AppraisalEngine
from emotion_os.core import AffectState, AgentProfile, Event, EventCategory, Goal, Personality, StateFactors
from emotion_os.generation import EmotionGenerator
from emotion_os.generation.intensity import LOSS_AVERSION, episode_intensity

BASE = AgentProfile(
    agent_id="me",
    goals={"money": Goal("money", importance=0.8)},
    personality=Personality(neuroticism=0.5, extraversion=0.5),
)


def run(e: Event, a: AgentProfile = BASE):
    r = AppraisalEngine().appraise(e, a)
    return EmotionGenerator().generate(r, e, a, AffectState()), r


class TestZeroRelevance:
    def test_zero_relevance_zero_activation(self):
        """R-INT-01：目标相关性=0 → 一切激活=0（G2 反例-1：无关葬礼无情绪）。"""
        stranger_loss = Event(category=EventCategory.LOSS, description="陌生人远亲的葬礼")
        g1, r1 = run(stranger_loss, AgentProfile(goals={"craft": Goal("craft", importance=0.9)}))
        assert r1.goal_relevance <= 0.02
        assert g1.episodes == []

        # 对照：对有该目标关联的主体，同类事件（不可逆损失）→ 悲伤族强激活
        kin_agent = AgentProfile(goals={"craft": Goal("craft", importance=0.9)})
        kin_loss = Event(category=EventCategory.LOSS, goal_impacts={"craft": -0.9}, reversibility=0.0)
        g2, r2 = run(kin_loss, kin_agent)
        assert r2.goal_relevance > 0.5
        acts = {ep.category: ep.intensity for ep in g2.episodes}
        assert acts.get("sadness", 0) > 0.2


class TestLossAversion:
    def test_loss_aversion_asymmetry(self):
        """R-INT-02：丢 100 的痛 ≈ 得 200 的乐（λ≈2；对称化违反前景理论）。"""
        # 等工具人主体（中性人格、无状态放大）
        neutral = AgentProfile(
            agent_id="me",
            goals={"money": Goal("money", importance=0.8)},
            personality=Personality(neuroticism=0.5, extraversion=0.5),
        )
        loss_small = Event(category=EventCategory.LOSS, goal_impacts={"money": -0.2}, reversibility=0.0)
        gain_double = Event(category=EventCategory.ACHIEVEMENT, goal_impacts={"money": 0.4})
        gl, _ = run(loss_small, neutral)
        gd, _ = run(gain_double, neutral)
        pain = {ep.category: ep.intensity for ep in gl.episodes}.get("sadness", 0.0)
        pleasure = {ep.category: ep.intensity for ep in gd.episodes}.get("joy", 0.0)
        # 同幅度对照
        gain_small = Event(category=EventCategory.ACHIEVEMENT, goal_impacts={"money": 0.2})
        gs, _ = run(gain_small, neutral)
        pleasure_small = {ep.category: ep.intensity for ep in gs.episodes}.get("joy", 0.0)

        assert pain > 1.6 * pleasure_small            # 同幅度：痛显著大于乐
        assert abs(pain - pleasure) < 0.25 * max(pain, pleasure)  # 双倍幅度才追平
        assert LOSS_AVERSION == 2.0                   # 待标定值显式记录


class TestMultiplicativeFactors:
    def test_neuroticism_scales_negative(self):
        stable = AgentProfile(
            agent_id="me", goals={"money": Goal("money", importance=0.8)},
            personality=Personality(neuroticism=0.1, extraversion=0.5),
        )
        reactive = AgentProfile(
            agent_id="me", goals={"money": Goal("money", importance=0.8)},
            personality=Personality(neuroticism=0.9, extraversion=0.5),
        )
        e = Event(category=EventCategory.LOSS, goal_impacts={"money": -0.5}, reversibility=0.5)
        g_stable, _ = run(e, stable)
        g_reactive, _ = run(e, reactive)
        s1 = {ep.category: ep.intensity for ep in g_stable.episodes}.get("sadness", 0.0)
        s2 = {ep.category: ep.intensity for ep in g_reactive.episodes}.get("sadness", 0.0)
        assert s2 > s1

    def test_sleep_deprivation_amplifies_negative(self):
        rested = AgentProfile(goals={"money": Goal("money", importance=0.8)})
        deprived = AgentProfile(
            goals={"money": Goal("money", importance=0.8)},
            state=StateFactors(sleep_deprivation=0.9),
        )
        e = Event(category=EventCategory.LOSS, goal_impacts={"money": -0.5}, reversibility=0.5)
        g1, _ = run(e, rested)
        g2, _ = run(e, deprived)
        s1 = {ep.category: ep.intensity for ep in g1.episodes}.get("sadness", 0.0)
        s2 = {ep.category: ep.intensity for ep in g2.episodes}.get("sadness", 0.0)
        assert s2 > s1

    def test_arousal_residue_boosts_high_arousal(self):
        e = Event(category=EventCategory.ACHIEVEMENT, goal_impacts={"money": 0.6}, novelty=0.6)
        plain = AffectState()
        wired = AffectState(arousal_residue=0.8)   # 前置紧张残余（兴奋转移）
        a = BASE
        r = AppraisalEngine().appraise(e, a)
        g1 = EmotionGenerator().generate(r, e, a, plain)
        g2 = EmotionGenerator().generate(r, e, a, wired)
        hi1 = {ep.category: ep.intensity for ep in g1.episodes}.get("excitement", 0.0)
        hi2 = {ep.category: ep.intensity for ep in g2.episodes}.get("excitement", 0.0)
        assert hi2 > hi1

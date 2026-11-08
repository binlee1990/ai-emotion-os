"""场景扩展：短剧/网文循环（调研 §5.4 爽点结构、2024–2025 中文权威来源）。

压抑→反转→钩子全循环；重生确定性爽感（新华网 2025）；甜宠磕糖习惯化；追更残余放大。
"""
from __future__ import annotations

from emotion_os import AgentProfile, BondInfo, EmotionEngine, Event, EventCategory, Goal, Intent, MoralInfo


def binge_viewer() -> AgentProfile:
    return AgentProfile.reader_example()


def humiliation():
    return Event(
        category=EventCategory.VIOLATION,
        description="反派当众羞辱主角", affects="self",
        caused_by="villain", intent=Intent.DELIBERATE,
        goal_impacts={"esteem": -0.6},
        moral=MoralInfo(severity=0.6, victim="self", violator="villain"),
        control_hint=0.2, fictionality=1.0, safety_frame=1.0,
    )


def reversal():
    return Event(
        category=EventCategory.VIOLATION,
        description="主角当众反杀", affects="self",
        goal_impacts={"justice": 0.8, "esteem": 0.5},
        justice_restored=0.9, justice_target="villain",
        prior_adversity_resolved=True, effort=0.7,
        fictionality=1.0, safety_frame=1.0,
    )


def cliffhanger(probability: float = 0.5, expectancy: float = 0.6):
    return Event(
        category=EventCategory.THREAT,
        description="片尾更强敌人登场（钩子）", affects="self",
        goal_impacts={"esteem": -0.4},
        probability=probability, urgency=0.8, expectancy_violation=expectancy,
        novelty=0.7, control_hint=0.3,
        fictionality=1.0, safety_frame=1.0,
    )


def acts(result):
    return {ep.category: ep.intensity for ep in result.episodes}


class TestFullCycle:
    def test_suppress_reversal_hook(self):
        """压抑期(憋屈)→反转(解气/爽)→钩子(悬念/期待挂住下一集)。"""
        eng = EmotionEngine(binge_viewer())
        a1 = acts(eng.process(humiliation(), dt_minutes=2.0))
        assert a1.get("bie_qu", 0) > 0.2 and a1.get("indignation", 0) > 0.2
        a2 = acts(eng.process(reversal(), dt_minutes=2.0))
        assert a2.get("jie_qi", 0) > 0.3 and a2.get("shuang", 0) > 0.2
        r3 = eng.process(cliffhanger(), dt_minutes=2.0)
        a3 = acts(r3)
        assert a3.get("suspense", 0) > 0.1 or a3.get("anticipation", 0) > 0.05
        # 钩子挂着：10 分钟后张力仍未清零（Zeigarnik 式未完成）
        eng.dynamics.tick(eng.state, 10.0)
        assert eng.state.activation("suspense") + eng.state.activation("anticipation") > 0.03


class TestRebirthCertainty:
    def test_omniscient_hero_feels_less_suspense(self):
        """重生设定=全知：悬念更低且期待更高（确定性爽感，§5.4.4）。
        全知带来的掌控感操作化为 esteem 的轻微正收益（成竹在胸）。"""
        eng_plain = EmotionEngine(binge_viewer())
        eng_reborn = EmotionEngine(binge_viewer())
        a_plain = acts(eng_plain.process(cliffhanger(probability=0.5, expectancy=0.6), dt_minutes=1.0))
        reborn_ev = Event(
            category=EventCategory.THREAT,
            description="重生者胸有成竹地走进同一局", affects="self",
            goal_impacts={"esteem": 0.15},          # 全知=确定的优势
            probability=0.98, urgency=0.8, expectancy_violation=0.05,
            novelty=0.7, control_hint=0.3, fictionality=1.0, safety_frame=1.0,
        )
        a_reborn = acts(eng_reborn.process(reborn_ev, dt_minutes=1.0))
        assert a_reborn.get("suspense", 0) < 0.5 * a_plain.get("suspense", 1.0)
        assert a_reborn.get("anxiety", 0) < a_plain.get("anxiety", 1.0)
        # 确定性爽感的正性侧：全知者的确定收益在场（喜悦/满足），普通观众悬置中无正性收益
        reborn_gain = a_reborn.get("joy", 0) + a_reborn.get("contentment", 0)
        plain_gain = a_plain.get("joy", 0) + a_plain.get("contentment", 0)
        assert reborn_gain > 0.1 and reborn_gain > plain_gain


class TestSweetPet:
    def test_kedao_habituates_with_repetition_but_variety_sustains(self):
        """磕糖：同一颗糖重复会腻（习惯化），换糖持续有效（§4.4 vs 变率）。"""
        same = EmotionEngine(binge_viewer())
        varied = EmotionEngine(binge_viewer())

        def sugar(key: str):
            return Event(
                category=EventCategory.BOND, affects="fictional:cp",
                bond=BondInfo(delta=0.7, sudden=True, romantic=True),
                stimulus_key=key, fictionality=1.0, safety_frame=1.0,
            )

        v1 = same.process(sugar("sugar-A"), dt_minutes=5.0).state.activation("ke_dao")
        same.process(sugar("sugar-A"), dt_minutes=5.0)
        v3 = same.process(sugar("sugar-A"), dt_minutes=5.0).state.activation("ke_dao")
        w1 = varied.process(sugar("sugar-A"), dt_minutes=5.0).state.activation("ke_dao")
        varied.process(sugar("sugar-B"), dt_minutes=5.0)
        w3 = varied.process(sugar("sugar-C"), dt_minutes=5.0).state.activation("ke_dao")

        assert v3 < 0.8 * v1          # 重复同一颗糖 → 衰减（习惯化乘数 0.85²≈0.72）
        assert w3 > 0.9 * w1          # 换糖 → 维持


class TestBingeResidue:
    def test_cliffhanger_amplifies_next_payoff(self):
        """兴奋转移（§1.5.2）：钩子留下的唤醒残余放大下一集的解脱。"""
        wired = EmotionEngine(binge_viewer())
        fresh = EmotionEngine(binge_viewer())
        wired.process(cliffhanger(), dt_minutes=1.0)                    # 刚看完钩子
        payoff = Event(
            category=EventCategory.THREAT,
            description="下一集开篇危机解除", affects="self",
            goal_impacts={"esteem": 0.5}, prior_threat_resolved=True,
            probability=1.0, fictionality=1.0, safety_frame=1.0,
        )
        r_wired = wired.process(payoff, dt_minutes=1.0)
        r_fresh = fresh.process(payoff, dt_minutes=1.0)
        assert acts(r_wired).get("relief", 0) > acts(r_fresh).get("relief", 0)

    def test_consecutive_hooks_give_shang_tou(self):
        """上头（§3.3）：连续钩子让 wanting 池压过 liking 池（wanting≠liking 的追更状态）。"""
        eng = EmotionEngine(binge_viewer())
        for _ in range(3):
            eng.process(cliffhanger(), dt_minutes=1.0)
        assert eng.state.wanting_pool > 1.5 * (eng.state.liking_pool + 0.2)
        assert eng.state.activation("shang_tou") > 0.05

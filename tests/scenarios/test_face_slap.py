"""场景1：短剧打脸（调研 §5.4 爽点结构；grammar R-APP-02）。

压抑期（违范+下行比较+低控制→愤怒-委屈-憋屈）→ 反转（惩罚达成→解气+爽）。
代入视角：运输理论下虚构事件与真实事件共享情绪通路（调研 §1.5.7），
故以 affects="self" + fictionality=1 建模观众对主角的认同。
"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Intent, MoralInfo


def reader() -> AgentProfile:
    return AgentProfile.reader_example()


def humiliation(engine_dt: float = 2.0):
    """反派当众羞辱主角（观众代入）。"""
    return Event(
        category=EventCategory.VIOLATION,
        description="反派当众羞辱主角并夺走其成果",
        affects="self", caused_by="villain", intent=Intent.DELIBERATE,
        goal_impacts={"esteem": -0.7},
        moral=MoralInfo(severity=0.7, victim="self", violator="villain"),
        control_hint=0.2,                      # 主角暂时无力反抗
        fictionality=1.0, safety_frame=1.0,
    )


def face_slap():
    """反派身份曝光、主角当众反杀（正义恢复+战胜逆境）。"""
    return Event(
        category=EventCategory.VIOLATION,
        description="反派身份曝光当众伏诛",
        affects="self",
        goal_impacts={"justice": 0.8, "esteem": 0.4},
        justice_restored=0.9, justice_target="villain",   # 受罚方=先前违规者
        prior_adversity_resolved=True, effort=0.7,   # 主角战胜先前逆境 → fiero
        fictionality=1.0, safety_frame=1.0,
    )


def wrong_target_punishment(agent_id: str):
    """罚错对象：惩罚了无关路人（受罚方 ≠ 先前违规者）。"""
    return Event(
        category=EventCategory.VIOLATION,
        description="误罚无辜路人",
        affects="self",
        goal_impacts={"justice": 0.8},
        justice_restored=0.9, justice_target="bystander",
        caused_by=agent_id,                    # 自己执行的惩罚 → 误伤无辜归因于自身
        moral=MoralInfo(severity=0.7, victim="bystander", violator=agent_id),
        fictionality=1.0, safety_frame=1.0,
    )


def acts(result):
    return {ep.category: ep.intensity for ep in result.episodes}


class TestSuppressionPhase:
    def test_humiliation_yields_indignation_weiwan_biequ_not_rage(self):
        eng = EmotionEngine(reader())
        r = eng.process(humiliation(), dt_minutes=2.0)
        a = acts(r)
        # 憋屈期：义愤、委屈、憋屈都在
        assert a.get("indignation", 0) > 0.2
        assert a.get("wei_yuan", 0) > 0.15
        assert a.get("bie_qu", 0) > 0.2
        # 低控制 → 愤怒被压制（不会当场爆发）
        assert a.get("anger", 0) < a.get("bie_qu", 0)


class TestFaceSlapPhase:
    def test_two_phase_relief_trajectory(self):
        eng = EmotionEngine(reader())
        eng.process(humiliation(), dt_minutes=2.0)
        r2 = eng.process(face_slap(), dt_minutes=2.0)
        a2 = acts(r2)
        # 打脸：解气、爽、胜利感
        assert a2.get("jie_qi", 0) > 0.3
        assert a2.get("shuang", 0) > 0.2
        assert a2.get("fiero", 0) > 0.1
        # 解气高于残余愤怒
        assert a2.get("jie_qi", 0) > a2.get("anger", 0)
        # 表达层输出中文词
        assert r2.expression.entries
        words = "、".join(e.word for e in r2.expression.entries)
        assert any(k in words for k in ("解气", "大快人心", "爽", "痛快", "酣畅淋漓"))

    def test_no_prior_indignation_no_relief(self):
        """R-APP-02 反例：无前置义愤的惩罚不产生解气。"""
        eng = EmotionEngine(reader())          # 未经历压抑期
        r = eng.process(face_slap(), dt_minutes=2.0)
        a = acts(r)
        assert a.get("jie_qi", 0) < 0.05       # 无解气
        assert a.get("shuang", 0) < 0.05       # 无憋屈可释放 → 无爽

    def test_wrong_punishment_target_no_relief_but_guilt(self):
        """R-APP-02 反例：罚错对象（受罚方≠违规者）→ 无解气；自己误罚无辜 → 内疚。"""
        eng = EmotionEngine(reader())
        eng.process(humiliation(), dt_minutes=2.0)          # 义愤指向 villain
        r = eng.process(wrong_target_punishment(eng.agent.agent_id), dt_minutes=2.0)
        a = acts(r)
        assert a.get("jie_qi", 0) < 0.05       # 记账不匹配 → 无解气
        assert a.get("guilt", 0) > 0.1         # 自伤无辜 → 内疚（OCC 复合语义）

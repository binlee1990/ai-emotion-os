"""场景3：运动/社交（调研 §5.6 运动 · 体育、§5.7 社交/社交媒体）。

六断言组：
  沾光（BIRGing：我队胜利→替代性狂喜/喜悦）、切割（CORFing 侧：惨败→自我价值受挫无喜悦）、
  绝杀兴奋转移（悬念残余唤醒放大后续胜利情绪，§4.3/§5.6「绝杀=fiero×兴奋转移」）、
  跑者高潮（中等强度有氧→活力/愉悦，§5.6 内源性大麻素）、
  已读不回（§5.7 社会疼痛/焦虑——引擎表现为憋屈+挫折+恐惧族）、
  热搜义愤→解气（§5.7 集体义愤高传播 + 惩罚意愿，跨事件 charges）。
"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, Personality
from emotion_os.core.event import MoralInfo
from emotion_os.core.types import Intent


def fan() -> AgentProfile:
    """球迷/网友画像：认同我队（liking +0.9）、反感对手与塌房明星。"""
    return AgentProfile(
        agent_id="fan",
        goals={
            "esteem": Goal("esteem", "自尊与地位", 0.8),
            "justice": Goal("justice", "公平得到伸张", 0.7),
            "bond": Goal("bond", "亲密联结", 0.8),
        },
        personality=Personality(neuroticism=0.5, extraversion=0.6),
        regulation_capacity=0.5, empathic_trait=0.5,
        liking={"team_red": 0.9, "team_blue": -0.6, "star_liu": -0.5},
    )


def run_seq(events: list[tuple[Event, float]], agent: AgentProfile | None = None) -> list[dict[str, float]]:
    eng = EmotionEngine(agent or fan())
    out = []
    for ev, dt in events:
        r = eng.process(ev, dt_minutes=dt)
        out.append({ep.category: ep.intensity for ep in r.episodes})
    return out


def buzzer_beater() -> Event:
    return Event(
        category=EventCategory.ACHIEVEMENT, description="压哨绝杀",
        affects="group:team_red", caused_by="team_red", intent=Intent.DELIBERATE,
        goal_impacts={"esteem": 0.7}, novelty=0.9, pleasantness=0.95,
        expectancy_violation=0.95, probability=0.15, urgency=0.95,
        effort=0.85, prior_adversity_resolved=True, prior_threat_resolved=True,
    )


class TestSpectator:
    def test_birging_reflected_glory(self):
        """§5.6 BIRGing：认同球队的胜利 → 替代性喜悦与狂喜（fiero×joy）。"""
        r = run_seq([(
            Event(
                category=EventCategory.ACHIEVEMENT, description="我队绝杀获胜",
                affects="group:team_red", caused_by="team_red", intent=Intent.DELIBERATE,
                goal_impacts={"esteem": 0.7}, novelty=0.8, pleasantness=0.9,
                expectancy_violation=0.9, probability=0.2, urgency=0.9,
                effort=0.8, prior_adversity_resolved=True,
            ), 1.0)])[0]
        assert r.get("fiero", 0) > 0.4, f"fiero={r.get('fiero')}"
        assert r.get("joy", 0) > 0.4, f"joy={r.get('joy')}"

    def test_corfing_self_worth_hit(self):
        """§5.6 CORFing 侧：群体认同=自我认同一部分——惨败 → 无替代喜悦、憋屈/挫折（自我价值受挫）。

        （切割的疏远行为属行为层，不在本引擎范围；这里断言其情绪底座。）
        """
        r = run_seq([(
            Event(
                category=EventCategory.LOSS, description="我队惨败",
                affects="group:team_red", caused_by="team_blue", intent=Intent.DELIBERATE,
                goal_impacts={"esteem": -0.7}, novelty=0.4, pleasantness=-0.8,
                expectancy_violation=0.6, probability=0.85,
            ), 1.0)])[0]
        assert r.get("joy", 0) < 0.1, f"joy={r.get('joy')}"
        assert max(r.get("bie_qu", 0), r.get("frustration", 0)) > 0.4


class TestExcitationTransfer:
    @staticmethod
    def stalemate() -> Event:
        return Event(
            category=EventCategory.FRUSTRATION, description="落后僵持最后时刻",
            affects="group:team_red", caused_by="team_blue", intent=Intent.DELIBERATE,
            goal_impacts={"esteem": -0.4}, novelty=0.3, pleasantness=-0.5,
            expectancy_violation=0.5, probability=0.5, urgency=0.95,
        )

    def test_buzzer_beater_amplified_by_suspense(self):
        """§5.6/§4.3：绝杀=fiero×兴奋转移——前置悬念的残余唤醒放大胜利情绪（relief/fiero 均高于无悬念直胜）。"""
        with_suspense = run_seq([(self.stalemate(), 2.0), (buzzer_beater(), 0.5)])[1]
        without = run_seq([(buzzer_beater(), 0.5)])[0]
        assert with_suspense.get("relief", 0) - without.get("relief", 0) > 0.1, (
            f"relief: {with_suspense.get('relief')} vs {without.get('relief')}")
        assert with_suspense.get("fiero", 0) - without.get("fiero", 0) > 0.1, (
            f"fiero: {with_suspense.get('fiero')} vs {without.get('fiero')}")

    def test_transfer_decays_over_residual_window(self):
        """R-DYN-03 反例边界：前置悬念久远（≫残余半衰期 10min）时转移归零——
        120 分钟后的同等成就与无悬念直胜一致（v0.3 时序修复后 process 先衰减再生成）。"""
        distant = run_seq([(self.stalemate(), 2.0), (buzzer_beater(), 120.0)])[1]
        without = run_seq([(buzzer_beater(), 0.5)])[0]
        assert distant.get("relief", 0) - without.get("relief", 0) < 0.05, (
            f"relief: {distant.get('relief')} vs {without.get('relief')}")
        assert distant.get("fiero", 0) - without.get("fiero", 0) < 0.05, (
            f"fiero: {distant.get('fiero')} vs {without.get('fiero')}")


class TestRunnerHigh:
    def test_moderate_aerobic_vitality(self):
        """§5.6 跑者高潮：中等强度有氧 → 活力+愉悦+放松（AEA 机制的情绪侧）。"""
        r = run_seq([(
            Event(
                category=EventCategory.BODY, description="中等强度跑步40分钟",
                affects="self", caused_by="self", intent=Intent.DELIBERATE,
                goal_impacts={"health": 0.4}, novelty=0.2, pleasantness=0.7,
                probability=1.0, effort=0.6,
            ), 40.0)])[0]
        assert r.get("vitality", 0) > 0.25, f"vitality={r.get('vitality')}"
        assert r.get("pleasure", 0) > 0.25, f"pleasure={r.get('pleasure')}"
        assert r.get("relaxation", 0) > 0.05


class TestSocialMedia:
    def test_read_no_reply_rejection(self):
        """§5.7 已读不回：联结受挫 + 结果不确定（对方为何不回）→ 焦虑（不确定弥散）
        + 憋屈/挫折（社会疼痛回路 dACC 预测的族级读法：疼痛/焦虑/嫉妒族）。"""
        r = run_seq([(
            Event(
                category=EventCategory.FRUSTRATION, description="暧昧对象已读不回两小时",
                affects="self", caused_by="crush", intent=Intent.UNKNOWN,
                goal_impacts={"bond": -0.5}, novelty=0.5, pleasantness=-0.6,
                expectancy_violation=0.8, probability=0.6, urgency=0.5, control_hint=0.2,
            ), 1.0)])[0]
        assert r.get("frustration", 0) > 0.5, f"frustration={r.get('frustration')}"
        assert r.get("bie_qu", 0) > 0.5, f"bie_qu={r.get('bie_qu')}"
        assert r.get("anxiety", 0) > 0.2, f"anxiety={r.get('anxiety')}"

    def test_hot_search_indignation_then_jieqi(self):
        """§5.7 热搜不公：集体义愤（E 违范）→ 惩罚落地 → 解气+爽（跨事件 charges 机制）。"""
        scandal = Event(
            category=EventCategory.VIOLATION, description="顶流刘某偷税上热搜",
            affects="public", caused_by="star_liu", intent=Intent.DELIBERATE,
            goal_impacts={"justice": -0.8}, novelty=0.9, pleasantness=-0.8,
            expectancy_violation=0.7, probability=1.0,
            moral=MoralInfo(severity=0.85, victim="public", violator="star_liu", virtue=False),
        )
        punish = Event(
            category=EventCategory.ACHIEVEMENT, description="刘某被封杀罚款",
            affects="star_liu", caused_by="authority", intent=Intent.DELIBERATE,
            goal_impacts={"justice": 0.8}, novelty=0.8, pleasantness=0.8,
            expectancy_violation=0.6, probability=1.0,
            justice_restored=0.95, justice_target="star_liu",
        )
        after1, after2 = run_seq([(scandal, 1.0), (punish, 5.0)])
        assert after1.get("indignation", 0) > 0.5, f"indignation={after1.get('indignation')}"
        assert after2.get("jie_qi", 0) > 0.5, f"jie_qi={after2.get('jie_qi')}"
        assert after2.get("shuang", 0) > 0.3, f"shuang={after2.get('shuang')}"

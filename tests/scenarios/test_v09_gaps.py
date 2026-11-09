"""v0.9 情绪类别层缺口场景测试：七个评价结构独立、此前折入邻近类的情绪类别
（架构合同 §8 v0.9 候选清单；grammar R-APP-11..17 的 formal_check 承载）。

① 屈辱 humiliation（Torres & Bergner：公开+他人施加+不应得+无防御）
② 仇恨 hatred（OCC 复合：不可逆伤害×施加者×态度化持续）
③ 自负 hubristic pride（Tangney & Tracy 双型：低努力=全局自我归因代理）
④ 错失恐惧 FOMO（Przybylski 2013：他人获益+自身缺席+窗口）
⑤ 崇拜 adoration（Cowen 27 唯一缺项：devotion 对象属性第三型）
⑥ 自怜 self-pity（HUMAINE：委屈×无人看见的自我沉溺）
⑦ 物哀 mono no aware（HUMAINE：美好×将逝的无常品味）
"""
from __future__ import annotations

from emotion_os import (
    AestheticInfo, AgentProfile, BondInfo, EmotionEngine, Event, EventCategory,
    Goal, MoralInfo,
)


def acts(result) -> dict[str, float]:
    return {ep.category: ep.intensity for ep in result.episodes}


def agent_with(**kw) -> AgentProfile:
    """默认画像：justice/esteem/bond 目标在场，可覆写 liking 等。"""
    return AgentProfile(
        agent_id="v09-agent",
        goals={
            "justice": Goal("justice", "公平得到伸张", 0.8),
            "esteem": Goal("esteem", "自尊与地位", 0.7),
            "bond": Goal("bond", "亲密联结", 0.7),
        },
        **kw,
    )


# ---------------- ① 屈辱（R-APP-11）----------------

def demean_event(public: float) -> Event:
    return Event(
        category=EventCategory.VIOLATION,
        description="庆功宴上被上司当众摔文件羞辱" if public > 0.2 else "办公室里被上司严厉批评",
        affects="self",
        caused_by="boss",
        moral=MoralInfo(severity=0.8, victim="self", violator="boss"),
        public_setting=public,
        control_hint=0.2,          # 无防御（当众无法回嘴）
        expectancy_violation=0.6,
    )


class TestHumiliation:
    def test_public_demeaning_humiliation(self):
        """正例：当众贬低 → 屈辱出场（公开×他人施加×不应得×无防御）。"""
        eng = EmotionEngine(agent_with())
        a = acts(eng.process(demean_event(public=0.9), dt_minutes=1.0))
        assert a.get("qu_ru", 0) > 0.4
        assert a.get("wei_yuan", 0) > 0.2          # 屈辱常含委屈

    def test_private_demeaning_no_humiliation(self):
        """反例：同一贬低私下发生（无观众）→ 委屈主导、屈辱不出场。"""
        eng = EmotionEngine(agent_with())
        a = acts(eng.process(demean_event(public=0.0), dt_minutes=1.0))
        assert "qu_ru" not in a
        assert a.get("wei_yuan", 0) > 0.2


# ---------------- ② 仇恨（R-APP-12）----------------

def irreversible_harm(reversibility: float, violator: str) -> Event:
    return Event(
        category=EventCategory.VIOLATION,
        description="凶手对至亲下毒手" if reversibility < 0.35 else "同事搞砸项目",
        affects="self",
        caused_by=violator,
        moral=MoralInfo(severity=0.9, victim="self", violator=violator),
        goal_impacts={"esteem": -0.5},
        reversibility=reversibility,
        expectancy_violation=0.5,
    )


class TestHatred:
    def test_irreversible_harm_hatred(self):
        """正例：不可逆伤害 × 施加者态度极负 → 仇恨。"""
        ag = agent_with(liking={"murderer": -0.9})
        eng = EmotionEngine(ag)
        a = acts(eng.process(irreversible_harm(0.1, "murderer"), dt_minutes=1.0))
        assert a.get("chou_hen", 0) > 0.4

    def test_reversible_harm_no_hatred(self):
        """反例1：可补救损失 × 陌生对象 → 仅愤怒/挫败，仇恨趋零。"""
        ag = agent_with()          # liking 无该对象 → 态度 0（非极负）
        eng = EmotionEngine(ag)
        a = acts(eng.process(irreversible_harm(0.8, "colleague"), dt_minutes=1.0))
        assert a.get("chou_hen", 0) < 0.1
        assert a.get("anger", 0) > 0.1 or a.get("frustration", 0) > 0.1

    def test_neutral_attitude_no_hatred(self):
        """反例2（态度隔离）：同不可逆伤害但施加者是陌生人（态度 0）→
        态度硬门压制仇恨——恨需要对象化的极负评价，单次伤害不产恨。"""
        ag = agent_with()          # 无 murderer liking → attitude_toward=0
        eng = EmotionEngine(ag)
        a = acts(eng.process(irreversible_harm(0.1, "stranger"), dt_minutes=1.0))
        assert "chou_hen" not in a
        assert a.get("grief", 0) > 0.1 or a.get("sadness", 0) > 0.1


# ---------------- ③ 自负（R-APP-13）----------------

def win_event(effort: float) -> Event:
    return Event(
        category=EventCategory.ACHIEVEMENT,
        description="碾压式夺冠" if effort < 0.5 else "十年苦练终夺冠",
        affects="self",
        caused_by="self",
        goal_impacts={"esteem": 0.8},
        effort=effort,
        expectancy_violation=0.3,
    )


class TestHubristicPride:
    def test_low_effort_hubristic_dominates(self):
        """正例1：轻松碾压（低努力=天赋归因）→ 自负 > 自豪。"""
        eng = EmotionEngine(agent_with())
        a = acts(eng.process(win_event(effort=0.1), dt_minutes=1.0))
        assert a.get("ao_man", 0) > 0.1
        assert a.get("ao_man", 0) > a.get("pride", 0)

    def test_high_effort_authentic_dominates(self):
        """正例2：十年苦练（高努力）→ 自豪主导，傲慢被硬门压零（两型竞争构念）。"""
        eng = EmotionEngine(agent_with())
        a = acts(eng.process(win_event(effort=0.9), dt_minutes=1.0))
        assert a.get("pride", 0) > a.get("ao_man", 0)
        assert a.get("pride", 0) > 0.2
        assert "ao_man" not in a

    def test_external_cause_no_hubris(self):
        """反例：成就归因他人/运气（caused_by=None）→ 自负不出场。"""
        eng = EmotionEngine(agent_with())
        e = Event(category=EventCategory.ACHIEVEMENT, description="运气好搭了顺风车",
                  affects="self", goal_impacts={"esteem": 0.8}, effort=0.1)
        a = acts(eng.process(e, dt_minutes=1.0))
        assert "ao_man" not in a


# ---------------- ④ 错失恐惧（R-APP-14）----------------

class TestFOMO:
    def test_missing_out_while_others_enjoy(self):
        """正例：他人正在获益+自身缺席+窗口临近 → 错失恐惧+wanting 注入。"""
        eng = EmotionEngine(agent_with())
        e = Event(
            category=EventCategory.BOND,
            description="好友群里直播聚会盛况，自己加班缺席",
            affects="self",
            fomo=0.8, urgency=0.7,
            expectancy_violation=0.4,
        )
        before = eng.state.wanting_pool
        a = acts(eng.process(e, dt_minutes=1.0))
        assert a.get("fomo", 0) > 0.3
        assert eng.state.wanting_pool > before
        assert a.get("boredom", 0) < a.get("fomo", 0)   # 缺席焦虑≠无聊（高投入态）

    def test_plain_deadline_no_fomo(self):
        """反例：普通截止焦虑（无社交缺席结构）→ 焦虑不出 fomo。"""
        eng = EmotionEngine(agent_with())
        e = Event(
            category=EventCategory.THREAT,
            description="普通工作截止日逼近",
            affects="self",
            goal_impacts={"esteem": -0.5},
            probability=0.5, urgency=0.8,
        )
        a = acts(eng.process(e, dt_minutes=1.0))
        assert "fomo" not in a
        assert a.get("anxiety", 0) > 0.1


# ---------------- ⑤ 崇拜（R-APP-15）----------------

class TestAdoration:
    def test_devotion_to_loved_idol(self):
        """正例：对喜爱对象的奉献性吸引 → 崇拜出场。"""
        ag = agent_with(liking={"idol": 0.8})
        eng = EmotionEngine(ag)
        e = Event(
            category=EventCategory.AESTHETIC,
            description="见到多年偶像本人",
            affects="idol",
            aesthetic=AestheticInfo(devotion=0.9),
            novelty=0.5, expectancy_violation=0.3,
        )
        a = acts(eng.process(e, dt_minutes=1.0))
        assert a.get("chong_bai", 0) > 0.2

    def test_disliked_object_lower_adoration(self):
        """反例：厌恶对象同等 devotion 信号 → 态度门压低崇拜。"""
        ag = agent_with(liking={"idol": 0.8, "idol2": -0.7})
        eng = EmotionEngine(ag)
        base = Event(
            category=EventCategory.AESTHETIC, description="偶像见面",
            aesthetic=AestheticInfo(devotion=0.9), novelty=0.5,
            expectancy_violation=0.3,
        )
        a_loved = acts(eng.process(
            Event(**{**base.__dict__, "affects": "idol"}), dt_minutes=1.0))
        a_disliked = acts(eng.process(
            Event(**{**base.__dict__, "affects": "idol2"}), dt_minutes=1.0))
        assert a_disliked.get("chong_bai", 0) < a_loved.get("chong_bai", 0)

    def test_skill_only_no_adoration(self):
        """反例2：纯技能见证（devotion=0）→ 钦佩而非崇拜。"""
        ag = agent_with(liking={"master": 0.6})
        eng = EmotionEngine(ag)
        e = Event(
            category=EventCategory.AESTHETIC, description="见证大师神级操作",
            affects="master",
            aesthetic=AestheticInfo(skill=0.8),
            novelty=0.4, expectancy_violation=0.3,
        )
        a = acts(eng.process(e, dt_minutes=1.0))
        assert "chong_bai" not in a
        assert a.get("admiration", 0) > 0.15


# ---------------- ⑥ 自怜（R-APP-16）----------------

def grievance_event(unseen: bool) -> Event:
    base = dict(
        category=EventCategory.VIOLATION,
        affects="self",
        caused_by="boss",
        moral=MoralInfo(severity=0.7, victim="self", violator="boss"),
        expectancy_violation=0.5,
    )
    if unseen:
        # 无人看见：叠加群体无视（invisibility 在场）
        return Event(description="当众被无视且被错待",
                     bond=BondInfo(delta=0.0, excluded=0.8), **base)
    return Event(description="被错待", **base)


class TestSelfPity:
    def test_grievance_unseen_self_pity(self):
        """正例：委屈 × 被无视 → 自怜（受害感的自我沉溺）。"""
        eng = EmotionEngine(agent_with())
        a = acts(eng.process(grievance_event(unseen=True), dt_minutes=1.0))
        assert a.get("wei_yuan", 0) > 0.3
        assert a.get("zi_lian", 0) > 0.15

    def test_grievance_with_support_no_self_pity(self):
        """反例：同委屈但无孤立信号 → 自怜不出场。"""
        eng = EmotionEngine(agent_with())
        a = acts(eng.process(grievance_event(unseen=False), dt_minutes=1.0))
        assert "zi_lian" not in a


# ---------------- ⑦ 物哀（R-APP-17）----------------

class TestMonoNoAware:
    def test_beauty_passing_awareness(self):
        """正例：美好在场 × 将逝觉察 → 物哀。"""
        eng = EmotionEngine(agent_with())
        e = Event(
            category=EventCategory.AESTHETIC,
            description="毕业最后一课，夕阳中的教室",
            affects="self",
            aesthetic=AestheticInfo(beauty=0.7),
            pleasantness=0.5,
            transience=0.8,
            expectancy_violation=0.3,
        )
        a = acts(eng.process(e, dt_minutes=1.0))
        assert a.get("wu_ai", 0) > 0.15
        assert a.get("beauty", 0) > 0.2           # 美好分量同时在座

    def test_beauty_without_passing_no_pathos(self):
        """反例1：同美好无将逝 → 仅美感，物哀不出场。"""
        eng = EmotionEngine(agent_with())
        e = Event(
            category=EventCategory.AESTHETIC,
            description="日常午后同样的教室",
            affects="self",
            aesthetic=AestheticInfo(beauty=0.7),
            pleasantness=0.5,
            expectancy_violation=0.3,
        )
        a = acts(eng.process(e, dt_minutes=1.0))
        assert "wu_ai" not in a

    def test_pure_loss_passing_no_pathos(self):
        """反例2（美好前提）：纯损失性终结（有将逝无美好）→ 悲伤而非物哀——
        美好是必要分量（乘法门），R-APP-17 edge_or_counter 的回归钉。"""
        eng = EmotionEngine(agent_with())
        e = Event(
            category=EventCategory.LOSS,
            description="项目彻底黄了，一切到此为止",
            affects="self",
            goal_impacts={"esteem": -0.6},
            pleasantness=-0.6,
            transience=0.8,
            reversibility=0.1,
        )
        a = acts(eng.process(e, dt_minutes=1.0))
        assert "wu_ai" not in a
        assert a.get("sadness", 0) > 0.15 or a.get("disappointment", 0) > 0.15

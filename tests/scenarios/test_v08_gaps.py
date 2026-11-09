"""v0.8 缺口场景测试：五个文献有独立地位、引擎此前折入或未建的事件域
（架构合同 §8 v0.8 候选清单落地；grammar R-APP-06..10 的 formal_check 承载）。

① 被排斥（Williams 需求威胁模型）——BondInfo.excluded
② 社交嬉戏（Panksepp PLAY）——PlayInfo
③ 对象特异渴望（Panksepp LUST 动机结构）——BondInfo.desire
④ 目标冲突/混合情绪（Larsen 2001 正负并存）——ambivalence 复合检测
⑤ 近失效应（Clark 2009/2010）——Event.near_miss
"""
from __future__ import annotations

from emotion_os import AgentProfile, BondInfo, EmotionEngine, Event, EventCategory, Goal, Personality, PlayInfo


def acts(result) -> dict[str, float]:
    return {ep.category: ep.intensity for ep in result.episodes}


def plain_agent(**kw) -> AgentProfile:
    """默认画像：esteem/bond 目标在场、中等调节，供各场景微调。"""
    return AgentProfile(
        agent_id="v08-agent",
        goals={"esteem": Goal("esteem", "自尊与地位", 0.7), "bond": Goal("bond", "亲密联结", 0.7)},
        **kw,
    )


# ---------------- ① 被排斥（R-APP-06）----------------

def exclusion_event(excluded: float, by_group: bool = True) -> Event:
    return Event(
        category=EventCategory.BOND,
        description="被群体无视" if by_group else "被个人拒之门外",
        affects="self",
        caused_by="group:roommates" if by_group else "stranger",
        bond=BondInfo(delta=0.0, sudden=True, break_up=False, excluded=excluded),
        expectancy_violation=0.6,   # 被无视出乎意料（RPE）
    )


class TestOstracism:
    def test_group_exclusion_pain_and_invisibility(self):
        """正例1：群体排斥（无既有关系）→ 社会疼痛 + 被无视感出场（Williams 反射性疼痛阶段）。"""
        eng = EmotionEngine(plain_agent())
        a = acts(eng.process(exclusion_event(0.8), dt_minutes=1.0))
        assert a.get("social_pain", 0) > 0.5
        assert a.get("invisibility", 0) > 0.3
        assert a.get("loneliness", 0) > 0.2

    def test_low_power_antisocial_path_anger(self):
        """正例2：力量感低（高神经质+低调节）+ 排斥重 → 反社会路径 anger 分量（Williams 反思阶段分流）。"""
        weak = plain_agent(personality=Personality(neuroticism=0.95))
        weak.regulation_capacity = 0.2
        eng_weak = EmotionEngine(weak)
        a_weak = acts(eng_weak.process(exclusion_event(0.9), dt_minutes=1.0))
        strong = plain_agent()
        strong.regulation_capacity = 0.9
        eng_strong = EmotionEngine(strong)
        a_strong = acts(eng_strong.process(exclusion_event(0.9), dt_minutes=1.0))
        # 低力量感者愤怒分量更高（power<0.4 → 外化攻击路径点燃）
        assert a_weak.get("anger", 0) > a_strong.get("anger", 0)

    def test_break_up_not_invisibility_dominated(self):
        """反例：特定关系断裂（break_up）→ heartbreak 主导而非 invisibility（两类语义分流）。"""
        eng = EmotionEngine(plain_agent())
        r = eng.process(
            Event(
                category=EventCategory.BOND,
                description="恋人明确提出分手",
                bond=BondInfo(delta=1.0, break_up=True),
            ),
            dt_minutes=1.0,
        )
        a = acts(r)
        assert a.get("heartbreak", 0) > 0.4
        assert "invisibility" not in a   # 断裂不点燃被无视感


# ---------------- ② 社交嬉戏（R-APP-07）----------------

def play_event(level: float, partnered: bool, safety: float = 1.0) -> Event:
    return Event(
        category=EventCategory.BODY,
        description="追逐打闹" if partnered else "独自动作游戏",
        affects="self",
        pleasantness=0.7,
        novelty=0.3,
        play=PlayInfo(level=level, partnered=partnered),
        safety_frame=safety,
    )


class TestPlay:
    def test_partnered_play_higher_than_solo(self):
        """正例1：有伴玩闹 > 独玩同等水平（PLAY 的社交加成）。"""
        eng_p = EmotionEngine(plain_agent())
        eng_s = EmotionEngine(plain_agent())
        a_p = acts(eng_p.process(play_event(0.8, True), dt_minutes=1.0))
        a_s = acts(eng_s.process(play_event(0.8, False), dt_minutes=1.0))
        assert a_p.get("play_joy", 0) > 0.5
        assert a_p.get("play_joy", 0) > a_s.get("play_joy", 0)

    def test_safety_frame_break_zeroes_play_joy(self):
        """反例：安全框架破损（对方真下重手）→ 玩闹欢腾趋零（真痛不是玩）。"""
        eng = EmotionEngine(plain_agent())
        a = acts(eng.process(play_event(0.8, True, safety=0.05), dt_minutes=1.0))
        assert a.get("play_joy", 0) < 0.2


# ---------------- ③ 对象特异渴望（R-APP-08）----------------

def longing_event(desire: float) -> Event:
    return Event(
        category=EventCategory.BOND,
        description="异地恋人月余未见，翻看聊天记录",
        bond=BondInfo(delta=0.3, sudden=False, romantic=True, desire=desire),
    )


class TestCraving:
    def test_longing_craving_over_flutter(self):
        """正例1：持续思念 → craving（朝思暮想）> heart_flutter（无新惊喜刺激）。"""
        eng = EmotionEngine(plain_agent())
        a = acts(eng.process(longing_event(0.8), dt_minutes=1.0))
        assert a.get("craving", 0) > 0.4
        assert a.get("craving", 0) > a.get("heart_flutter", 0)

    def test_wanting_pool_amplifies_repeated_longing(self):
        """正例2：wanting 池累积后同强度思念 → craving 放大（欲求缠身叠加）。"""
        eng = EmotionEngine(plain_agent())
        first = acts(eng.process(longing_event(0.8), dt_minutes=1.0))
        eng.dynamics.tick(eng.state, 30.0)   # 30 分钟：池部分衰减但余存
        second = acts(eng.process(longing_event(0.8), dt_minutes=1.0))
        assert second.get("craving", 0) > first.get("craving", 0)

    def test_companionship_no_craving(self):
        """反例：日常陪伴在侧（desire=0，联结正向）→ 依恋温暖主导，craving 不出场。"""
        eng = EmotionEngine(plain_agent())
        a = acts(
            eng.process(
                Event(
                    category=EventCategory.BOND,
                    description="恋人日常陪伴",
                    bond=BondInfo(delta=0.6, sudden=False, romantic=True),
                ),
                dt_minutes=1.0,
            )
        )
        assert "craving" not in a
        assert a.get("attachment_warmth", 0) > 0.1   # 温和在场（低强度是常态）


# ---------------- ④ 目标冲突/混合情绪（R-APP-09）----------------

def dilemma_event() -> Event:
    return Event(
        category=EventCategory.ACHIEVEMENT,
        description="升职外地 offer 到手，母亲重病留守老家",
        goal_impacts={"esteem": 0.8, "bond": -0.8},
        novelty=0.4,
        urgency=0.5,
        expectancy_violation=0.5,   # offer 意外来得不是时候
    )


class TestAmbivalence:
    def test_dilemma_ambivalence_activated(self):
        """正例1：正负目标等强并存（对消使 conduciveness=0）→ ambivalence 仍出场
        （冲突是评价输入层结构信号，不依赖输出层两侧激活巧合）。"""
        eng = EmotionEngine(plain_agent())
        a = acts(eng.process(dilemma_event(), dt_minutes=1.0))
        assert a.get("ambivalence", 0) > 0.4

    def test_pure_loss_no_ambivalence(self):
        """反例：纯损失（仅负侧激活）→ ambivalence 不出场。"""
        eng = EmotionEngine(plain_agent())
        a = acts(
            eng.process(
                Event(
                    category=EventCategory.LOSS,
                    description="项目彻底黄了，毫无转机",
                    goal_impacts={"esteem": -0.8},
                    reversibility=0.1,
                ),
                dt_minutes=1.0,
            )
        )
        assert "ambivalence" not in a

    def test_love_and_grievance_output_channel(self):
        """正例2（输出层通道）：深爱之人的错待 → 心动/激情与委屈（pass1 两侧）并存
        → ambivalence 出场——「又爱又怨」的正负原始情绪并存。"""
        from emotion_os import MoralInfo

        eng = EmotionEngine(plain_agent())
        a = acts(
            eng.process(
                Event(
                    category=EventCategory.BOND,
                    description="深爱的人当众让我难堪，但心里仍爱着",
                    bond=BondInfo(delta=0.8, sudden=True, romantic=True),
                    moral=MoralInfo(severity=0.7, victim="self", violator="lover"),
                    expectancy_violation=0.5,
                ),
                dt_minutes=1.0,
            )
        )
        assert a.get("romantic_passion", 0) > 0.35 or a.get("heart_flutter", 0) > 0.35
        assert a.get("wei_yuan", 0) > 0.35 or a.get("indignation", 0) > 0.35
        assert a.get("ambivalence", 0) > 0.35

    def test_kama_muta_po_fang_no_ambivalence(self):
        """回归反例（复审发现）：久别重逢 → kama_muta 与其派生 po_fang 双 1.0，
        但 po_fang 是同事件派生复合类（pass2），不作负侧 → 不得报矛盾。"""
        eng = EmotionEngine(plain_agent())
        r = eng.process(
            Event(
                category=EventCategory.BOND,
                description="失散多年母女重逢",
                bond=BondInfo(delta=1.0, sudden=True),
            ),
            dt_minutes=0.5,
        )
        a = acts(r)
        assert a.get("kama_muta", 0) > 0.6
        assert a.get("po_fang", 0) > 0.6
        assert a.get("ambivalence", 0) < 0.1


# ---------------- ⑤ 近失效应（R-APP-10）----------------

def lottery_event(near_miss: float) -> Event:
    return Event(
        category=EventCategory.ACHIEVEMENT,
        description="彩票开奖" if near_miss > 0 else "号码全不沾边",
        goal_impacts={"esteem": -0.6},
        expectancy_violation=0.7,
        near_miss=near_miss,
        probability=1.0,
    )


class TestNearMiss:
    def test_near_miss_vexation_and_retry_drive(self):
        """正例1：差一点 → 不甘心高激活 + wanting 池注入（再试驱动）。"""
        eng = EmotionEngine(plain_agent())
        before = eng.state.wanting_pool
        a = acts(eng.process(lottery_event(0.9), dt_minutes=1.0))
        assert a.get("bu_gan_xin", 0) > 0.4
        assert a.get("disappointment", 0) > 0.2
        assert eng.state.wanting_pool > before   # 再试驱动（池累积）

    def test_far_miss_no_vexation(self):
        """反例：差很远（near_miss=0）→ 只有失望，无不甘心。"""
        eng = EmotionEngine(plain_agent())
        a = acts(eng.process(lottery_event(0.0), dt_minutes=1.0))
        assert "bu_gan_xin" not in a
        assert a.get("disappointment", 0) > 0.05

    def test_near_miss_greater_retry_than_far(self):
        """正例2：差一点比差很远更想再来（wanting 注入对比）。"""
        eng_near = EmotionEngine(plain_agent())
        eng_far = EmotionEngine(plain_agent())
        eng_near.process(lottery_event(0.9), dt_minutes=1.0)
        eng_far.process(lottery_event(0.0), dt_minutes=1.0)
        assert eng_near.state.wanting_pool > eng_far.state.wanting_pool

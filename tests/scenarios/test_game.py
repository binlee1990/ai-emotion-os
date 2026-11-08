"""场景扩展：游戏（调研 §5.3 Lazzaro 四钥匙、CVT、变率强化、天梯比较）。"""
from __future__ import annotations

from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Goal, Personality, SocialInfo


def player() -> AgentProfile:
    a = AgentProfile(
        agent_id="gamer",
        goals={
            "mastery": Goal("mastery", "技术精进", 0.85),
            "rank": Goal("rank", "段位", 0.7),
            "loot": Goal("loot", "收藏/掉落", 0.6),
        },
        personality=Personality(neuroticism=0.4, extraversion=0.6, openness=0.7),
        sensation_seeking=0.7,
    )
    a.liking = {"rival": -0.6, "teammate": 0.7, "protege": 0.8}
    return a


def acts(result):
    return {ep.category: ep.intensity for ep in result.episodes}


class TestFourKeys:
    def test_hard_fun_frustration_to_fiero(self):
        """Hard Fun：高难挑战先挫败，战胜后 fiero（Lazzaro；McGonigal）。"""
        eng = EmotionEngine(player())
        stuck = Event(
            category=EventCategory.FRUSTRATION,
            description="卡关 47 次", affects="self",
            goal_impacts={"mastery": -0.6}, effort=0.8, control_hint=0.5,
        )
        a1 = acts(eng.process(stuck, dt_minutes=5.0))
        assert a1.get("frustration", 0) > 0.2
        cleared = Event(
            category=EventCategory.ACHIEVEMENT,
            description="终于通关", affects="self",
            goal_impacts={"mastery": 0.8},
            prior_adversity_resolved=True, effort=0.9,
        )
        a2 = acts(eng.process(cleared, dt_minutes=2.0))
        assert a2.get("fiero", 0) > 0.3

    def test_easy_fun_curiosity(self):
        e = Event(
            category=EventCategory.NOVELTY,
            description="发现隐藏地图", affects="self",
            goal_impacts={"mastery": 0.1}, novelty=0.8,
        )
        a = acts(EmotionEngine(player()).process(e, dt_minutes=1.0))
        assert a.get("curiosity", 0) > 0.2

    def test_people_fun_schadenfreude_and_naches(self):
        eng = EmotionEngine(player())
        rival_falls = Event(
            category=EventCategory.COMPARISON, affects="rival",
            social=SocialInfo(direction="down", deservedness=0.7),
        )
        a1 = acts(eng.process(rival_falls, dt_minutes=1.0))
        assert a1.get("schadenfreude", 0) > 0.1
        protege_wins = Event(
            category=EventCategory.COMPARISON, affects="protege",
            caused_by="gamer",                              # 我带的新人上分
            social=SocialInfo(direction="up", deservedness=0.9),
        )
        a2 = acts(eng.process(protege_wins, dt_minutes=1.0))
        assert a2.get("naches", 0) > 0.1

    def test_serious_fun_relaxation_habituates(self):
        eng = EmotionEngine(player())

        def zen() -> Event:
            return Event(
                category=EventCategory.BODY, description="节奏玩法解压", affects="self",
                pleasantness=0.5, novelty=0.05, stimulus_key="zen-mode",
            )

        r1 = eng.process(zen(), dt_minutes=10.0)
        eng.process(zen(), dt_minutes=10.0)
        r3 = eng.process(zen(), dt_minutes=10.0)
        assert acts(r3).get("relaxation", 0) < 0.9 * acts(r1).get("relaxation", 0)


class TestGacha:
    def _draw(self, ev: float, key: str | None) -> Event:
        return Event(
            category=EventCategory.ACHIEVEMENT, description="十连出货",
            affects="self", goal_impacts={"loot": 0.5},
            expectancy_violation=ev, novelty=0.4 + 0.4 * ev,
            stimulus_key=key,
        )

    def test_variable_reward_resists_habituation(self):
        """变率强化（§4.4/§1.5.1）：不可预测的奖赏逐次更新 surprise 并维持 wanting；
        固定奖赏在臂内跨次衰减（习惯化机制驱动，非臂间输入差异）。"""
        fixed = EmotionEngine(player())
        first = fixed.process(self._draw(0.05, "gacha"), dt_minutes=2.0)
        for _ in range(3):
            fixed.process(self._draw(0.05, "gacha"), dt_minutes=2.0)
        fixed_last = fixed.process(self._draw(0.05, "gacha"), dt_minutes=2.0)
        # 固定臂内：同输入第5次 vs 第1次——衰减只可能来自习惯化乘数（0.85^4≈0.52）
        assert acts(fixed_last).get("joy", 0) < 0.75 * acts(first).get("joy", 0)
        assert acts(fixed_last).get("surprise", 0) < 0.02

        variable = EmotionEngine(player())
        last_var = None
        for ev in (0.9, 0.1, 0.8, 0.2, 0.85):
            last_var = variable.process(self._draw(ev, "gacha"), dt_minutes=2.0)
        # 变率臂：第5次仍高 surprise——不可预测性逐次更新（RPE），抵抗习惯化压低
        assert acts(last_var).get("surprise", 0) > 0.1
        assert variable.state.wanting_pool > fixed.state.wanting_pool       # wanting 维持

        # 诚实探针：变率前史不改写机制——末次若可预测，surprise 与固定臂同级
        probe = EmotionEngine(player())
        for ev in (0.9, 0.1, 0.8, 0.2):
            probe.process(self._draw(ev, "gacha"), dt_minutes=2.0)
        probe_last = probe.process(self._draw(0.05, "gacha"), dt_minutes=2.0)
        assert abs(acts(probe_last).get("surprise", 0) - acts(fixed_last).get("surprise", 0)) < 0.01

    def test_near_miss_stings_more_than_clean_miss(self):
        """近失效应（§5.8 赌博行）：差一点比明确失败唤起更强情绪与更强 wanting（§1.5.1）。"""
        near = Event(
            category=EventCategory.LOSS, description="差一格没出金", affects="self",
            goal_impacts={"loot": -0.3}, expectancy_violation=0.85, novelty=0.7,
        )
        clean = Event(
            category=EventCategory.LOSS, description="全是蓝天", affects="self",
            goal_impacts={"loot": -0.3}, expectancy_violation=0.05, novelty=0.1,
        )
        eng_near = EmotionEngine(player())
        eng_clean = EmotionEngine(player())
        a_near = acts(eng_near.process(near, dt_minutes=1.0))
        a_clean = acts(eng_clean.process(clean, dt_minutes=1.0))
        response_near = a_near.get("surprise", 0) + a_near.get("disappointment", 0)
        response_clean = a_clean.get("surprise", 0) + a_clean.get("disappointment", 0)
        assert response_near > response_clean * 1.5
        assert eng_near.state.wanting_pool > eng_clean.state.wanting_pool   # 近失维持 wanting


class TestLadder:
    def test_rank_up_pride_rank_down_envy_shame(self):
        up = Event(
            category=EventCategory.COMPARISON, affects="self",
            goal_impacts={"rank": 0.6}, caused_by="gamer", effort=0.7,
        )
        a_up = acts(EmotionEngine(player()).process(up, dt_minutes=1.0))
        assert a_up.get("pride", 0) > 0.15
        down = Event(
            category=EventCategory.COMPARISON, affects="rival",
            social=SocialInfo(direction="up", deservedness=0.2),   # 对手靠代练上分
        )
        a_down = acts(EmotionEngine(player()).process(down, dt_minutes=1.0))
        assert a_down.get("malicious_envy", 0) > 0.1

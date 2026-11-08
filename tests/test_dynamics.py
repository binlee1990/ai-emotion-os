"""动力学单元测试（N7 出条件；承载 grammar R-DYN-01 / R-DYN-02 的 formal 声明）。"""
from __future__ import annotations

from emotion_os.core.state import AffectState, EmotionEpisode
from emotion_os.dynamics import AffectDynamics, HABITUATION_DECAY, MOOD_EMA_WEIGHT


class TestThreeLayers:
    def test_three_layer_time_scales(self):
        """R-DYN-01：情绪分钟级衰减；心情慢速 EMA 不被单事件翻转。"""
        dyn = AffectDynamics()
        state = AffectState(now_min=0.0)

        # 一次强愤怒（0.8）
        dyn.integrate(
            [EmotionEpisode("anger", 0.8, half_life_min=12.0)],
            state, event_valence=-0.6, event_arousal=0.7,
            event_importance=0.8, dt_minutes=0.0,
        )
        assert state.activation("anger") > 0.75

        # 40 分钟（>3 个半衰期）后 < 0.1 —— 情绪不过夜
        dyn.tick(state, 40.0)
        assert state.activation("anger") < 0.1

        # 单次强负事件后，心情效价只微降（≪情绪幅度），不翻转
        assert -MOOD_EMA_WEIGHT * 2.0 <= state.mood.valence <= -0.001
        assert abs(state.mood.valence) < 0.1

        # 24 小时后发作全部清理（哀恸 240 分钟半衰期也衰减殆尽）
        state2 = AffectState(now_min=0.0)
        dyn.integrate(
            [EmotionEpisode("grief", 0.9, half_life_min=240.0)],
            state2, event_valence=-0.85, event_arousal=0.5,
            event_importance=0.95, event_irreversibility=1.0, dt_minutes=0.0,
        )
        dyn.tick(state2, 1440.0)
        assert "grief" not in state2.episodes

    def test_inertia_merging_same_category(self):
        dyn = AffectDynamics()
        state = AffectState(now_min=0.0)
        dyn.integrate([EmotionEpisode("anger", 0.5)], state, -0.5, 0.6, dt_minutes=0.0)
        dyn.integrate([EmotionEpisode("anger", 0.5)], state, -0.5, 0.6, dt_minutes=1.0)
        assert state.activation("anger") > 0.75   # 残余+新激发叠加（情绪惯性）

    def test_arousal_residue_accumulates_and_decays(self):
        dyn = AffectDynamics()
        state = AffectState(now_min=0.0)
        dyn.integrate([EmotionEpisode("fear", 0.9, family="fear")], state, -0.7, 0.8, dt_minutes=0.0)
        before = state.arousal_residue
        assert before > 0.1
        dyn.tick(state, 60.0)
        assert state.arousal_residue < 0.25 * before

    def test_habituation_multiplier(self):
        dyn = AffectDynamics()
        state = AffectState()
        state.habituation["meme-42"] = 2
        m = dyn.habituation_multiplier("meme-42", state, set())
        assert abs(m - HABITUATION_DECAY ** 2) < 1e-9
        # 敏感化优先于习惯化
        assert dyn.habituation_multiplier("meme-42", state, {"meme-42"}) == 1.3

    def test_rumination_builds_on_irreversible_loss(self):
        dyn = AffectDynamics()
        state = AffectState()
        dyn.integrate([], state, -0.8, 0.4, event_importance=0.9, event_irreversibility=1.0)
        assert state.rumination > 0.25

    def test_wanting_liking_pools_asymmetric_decay(self):
        """v0.2：wanting 池衰减慢于 liking 池——「刷完空虚」的不对称基础（§1.5.1）。"""
        dyn = AffectDynamics()
        state = AffectState()
        ep_w = EmotionEpisode("curiosity", 0.6, family="epistemic", wanting=0.5, liking=0.1)
        ep_l = EmotionEpisode("joy", 0.6, family="joy", wanting=0.1, liking=0.5)
        dyn.integrate([ep_w, ep_l], state, 0.2, 0.5, dt_minutes=0.0)
        assert state.wanting_pool > 0.2 and state.liking_pool > 0.2
        dyn.tick(state, 30.0)   # 30 分钟：wanting 半衰 30min，liking 半衰 12min
        assert state.wanting_pool > state.liking_pool


class TestPeakEnd:
    def test_peak_end_duration_neglect(self):
        """R-DYN-02：记忆评分=峰+终；时长（事件数）不计。"""
        dyn = AffectDynamics()

        def run_session(n_good: int, end_valence: float) -> AffectState:
            state = AffectState()
            for _ in range(n_good):
                dyn.integrate([], state, 0.4, 0.5, dt_minutes=10.0)
            dyn.integrate([], state, end_valence, 0.8, event_importance=0.9, dt_minutes=5.0)
            return state

        short_be = run_session(3, end_valence=-0.8)
        long_be = run_session(12, end_valence=-0.8)     # 时长 4 倍
        he = run_session(3, end_valence=0.6)            # 同长，好结局

        # 时长忽视：短/长 BE 记忆评分几乎相同
        assert abs(short_be.memory.remembered_valence - long_be.memory.remembered_valence) < 1e-9
        # 终值权重：HE 显著优于 BE
        assert he.memory.remembered_valence > short_be.memory.remembered_valence + 0.5

"""动力学：情绪/心情/特质三层的演化（调研 §4.4；R-DYN-01/02；架构合同 §4.1）。

- integrate：新发作并入情绪层（同类别叠加=情绪惯性）、唤醒残余积累、心情慢速 EMA、
  峰终记忆观测、反刍积累（不可逆高重要性损失）、习惯化计数。
- tick：时间推进——发作指数衰减、残余与反刍慢衰减。
"""
from __future__ import annotations

import math

from ..core.state import AffectState, EmotionEpisode
from ..generation.catalog import CATALOG

# 待标定常数（调研附录：领域量化参数缺实证数值）
HABITUATION_DECAY = 0.85      # 每次重复暴露的激活乘数（§4.4 习惯化）
SENSITIZATION_GAIN = 1.3      # 敏感化线索放大（§4.2 创伤敏感化）
RESIDUE_HALF_LIFE = 10.0      # 唤醒残余半衰期（分钟）
RESIDUE_INTAKE = 0.5          # 发作唤醒进入残余的比例
MOOD_EMA_WEIGHT = 0.03        # 心情慢速权重（单事件≪1，R-DYN-01）
RUMINATION_HALF_LIFE = 300.0  # 反刍半衰期（意难平余韵，小时级）
RUMINATION_GAIN = 0.35        # 不可逆损失→反刍压力增量
CHARGE_HALF_LIFE = 120.0      # 对象记账（义愤/恶意羡慕）半衰期（分钟）


def _b01(x: float) -> float:
    return max(0.0, min(1.0, x))


class AffectDynamics:
    def habituation_multiplier(self, stimulus_key: str | None, state: AffectState, sensitized: set[str]) -> float:
        """重复刺激衰减 / 敏感化线索增强（先读后记：integrate 才递增计数）。"""
        if stimulus_key is None:
            return 1.0
        if stimulus_key in sensitized:
            return SENSITIZATION_GAIN
        n = state.habituation.get(stimulus_key, 0)
        return HABITUATION_DECAY ** n

    def integrate(
        self,
        episodes: list[EmotionEpisode],
        state: AffectState,
        event_valence: float,
        event_arousal: float,
        event_importance: float = 0.0,
        event_irreversibility: float = 0.0,
        dt_minutes: float = 0.0,
        charge_updates: dict[str, float] | None = None,
    ) -> AffectState:
        """一次事件后的状态更新。event_valence/arousal 取自该事件主导情绪的 4D 混合。"""
        state.now_min += dt_minutes
        if charge_updates:
            for target, strength in charge_updates.items():
                state.charges[target] = min(
                    1.5, max(state.charges.get(target, 0.0), strength)
                )

        peak_intensity = 0.0
        for ep in episodes:
            peak_intensity = max(peak_intensity, ep.intensity)
            residual = state.activation(ep.category) if ep.category in state.episodes else 0.0
            merged = _b01(residual + ep.intensity)          # 情绪惯性：残余叠加新激发
            state.episodes[ep.category] = EmotionEpisode(
                category=ep.category,
                intensity=merged,
                onset_min=state.now_min,
                half_life_min=max(ep.half_life_min, state.episodes.get(ep.category, ep).half_life_min if ep.category in state.episodes else ep.half_life_min),
                family=ep.family,
                wanting=ep.wanting,
                liking=ep.liking,
            )
            # 唤醒残余：高唤醒发作注入（兴奋转移 §1.5.2）
            cat = CATALOG[ep.category]
            state.arousal_residue = _b01(
                state.arousal_residue + RESIDUE_INTAKE * cat.arousal * ep.intensity
            )

        # 心情层：慢速 EMA（R-DYN-01：单事件不翻转心情）
        state.mood.update(event_valence, event_arousal, weight=MOOD_EMA_WEIGHT * (0.5 + 0.5 * event_importance))

        # 反刍：不可逆×高重要性损失累积（意难平来源，§3.3）
        state.rumination = min(2.0, state.rumination + RUMINATION_GAIN * event_importance * event_irreversibility)

        # 峰终记忆（R-DYN-02）
        state.memory.observe(event_valence, peak_intensity)
        return state

    def record_stimulus(self, stimulus_key: str | None, state: AffectState) -> None:
        if stimulus_key is not None:
            state.habituation[stimulus_key] = state.habituation.get(stimulus_key, 0) + 1

    def tick(self, state: AffectState, dt_minutes: float) -> AffectState:
        """时间推进：发作衰减清理、残余衰减、反刍衰减、调节资源缓慢恢复。"""
        state.now_min += dt_minutes
        dead = [
            cat for cat, ep in state.episodes.items() if ep.decayed(state.now_min) < 0.02
        ]
        for cat in dead:
            del state.episodes[cat]
        state.arousal_residue *= math.pow(0.5, dt_minutes / RESIDUE_HALF_LIFE)
        state.rumination *= math.pow(0.5, dt_minutes / RUMINATION_HALF_LIFE)
        state.regulation_depletion = max(0.0, state.regulation_depletion - 0.02 * dt_minutes / 10.0)
        if state.charges:
            decay = math.pow(0.5, dt_minutes / CHARGE_HALF_LIFE)
            state.charges = {t: v * decay for t, v in state.charges.items() if v * decay > 0.02}
        return state

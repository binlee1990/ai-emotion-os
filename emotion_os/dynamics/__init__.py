"""动力学：情绪/心情/特质三层的演化（调研 §4.4；R-DYN-01/02；架构合同 §4.1）。

- integrate：新发作并入情绪层（同类别叠加=情绪惯性）、唤醒残余积累、心情慢速 EMA、
  峰终记忆观测、反刍积累（不可逆高重要性损失）、习惯化计数。
- tick：时间推进——发作指数衰减、残余与反刍慢衰减。
"""
from __future__ import annotations

import math

from ..core.state import AffectState, EmotionEpisode
from ..generation.catalog import CATALOG

# 待标定常数（调研附录：领域量化参数缺实证数值；以下注记为 2026-11 检索核验的文献出处）
# 习惯化：文献无双时间尺度以外的单一「每步衰减率」——自主反应（SCR/心率）在前几次重复内快速
# 习惯化至渐近，LPP 情绪差异保持至 60–90 次重复（Codispoti, Ferrari & Bradley 2006, Brain Res
# 1068:213-220, doi:10.1016/j.brainres.2005.11.009；Codispoti et al. 2007；Ferrari et al. 2011,
# Psychophysiology 48:515-522）。0.85/次为自设值，非文献原值。
HABITUATION_DECAY = 0.85      # 每次重复暴露的激活乘数（§4.4 习惯化）
SENSITIZATION_GAIN = 1.3      # 敏感化线索放大（§4.2 创伤敏感化）
# 兴奋转移残余窗：Zillmann 1971 (JESP 7:419-434) 血管反应衰减 "as high as 3–5 minutes"；
# Bunce, Larsen & Cruz 1993 (PAID 15:409-418) 运动后 ~5.2 min 才恢复正常心率；
# Pedersen et al. 2017 综述：转移实验通常将激发-测量间隔限制在 5 min 内。半衰期 10 min
# 与「强残余 0–5 min、可测至 ~10 min」一致。
RESIDUE_HALF_LIFE = 10.0      # 唤醒残余半衰期（分钟）
RESIDUE_INTAKE = 0.5          # 发作唤醒进入残余的比例
# 情绪惯性参照：Kuppens, Allen & Sheeber 2010 (Psych Science 21:984-991) 经验取样 lag-1
# 自相关 0.20–0.33（间隔约 1.4h）；Houben et al. 2015 元分析 (Psych Bull 141:971-995)。
# 心情慢速 EMA 权重与之量级相容（换算依赖事件频率，非直接估计）。
MOOD_EMA_WEIGHT = 0.03        # 心情慢速权重（单事件≪1，R-DYN-01）
RUMINATION_HALF_LIFE = 300.0  # 反刍半衰期（意难平余韵，小时级；自设值）
RUMINATION_GAIN = 0.35        # 不可逆损失→反刍压力增量
CHARGE_HALF_LIFE = 120.0      # 对象记账（义愤/恶意羡慕）半衰期（分钟；自设值）
WANTING_HALF_LIFE = 30.0      # wanting 池半衰期（分钟）——慢于 liking（自设值，Berridge 无文献常数）
LIKING_HALF_LIFE = 12.0       # liking 池半衰期（分钟）——快衰减：快感留不住、欲求缠身


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
        repeat_stimulus: bool = False,
    ) -> AffectState:
        """一次事件后的状态更新。event_valence/arousal 取自该事件主导情绪的 4D 混合。

        合并语义（§4.4 两机制的边界）：新激发（repeat_stimulus=False）→ 残余叠加（升级/惯性）；
        同一刺激重复呈现（repeat_stimulus=True）→ 替换不叠加（重复衰减由习惯化乘数承担）。
        """
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
            merged = _b01(max(residual, ep.intensity) if repeat_stimulus else residual + ep.intensity)
            old_half_life = state.episodes[ep.category].half_life_min if ep.category in state.episodes else ep.half_life_min
            state.episodes[ep.category] = EmotionEpisode(
                category=ep.category,
                intensity=merged,
                onset_min=state.now_min,
                half_life_min=max(ep.half_life_min, old_half_life),
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

        # wanting/liking 双池（wanting≠liking 分账，§6.3.6）
        if episodes:
            state.wanting_pool = min(3.0, state.wanting_pool + sum(ep.wanting for ep in episodes))
            state.liking_pool = min(3.0, state.liking_pool + sum(ep.liking for ep in episodes))

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
        state.wanting_pool *= math.pow(0.5, dt_minutes / WANTING_HALF_LIFE)
        state.liking_pool *= math.pow(0.5, dt_minutes / LIKING_HALF_LIFE)
        return state

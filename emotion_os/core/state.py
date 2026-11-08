"""情感状态：情绪/心情/特质三层（调研 §4.4、架构合同 §4.1 动力学）。

- 情绪层：EmotionEpisode 激发→峰→衰减（分钟级半衰期；kama muta ≤2 分钟）。
- 心情层：MoodState 慢速 EMA（小时-天）。
- 特质层：AgentProfile（终身，不在此文件演化）。
附带：唤醒残余（兴奋转移 §1.5.2）、习惯化/敏感化、峰终记忆（§1.5.10）、反刍（意难平 §3.3）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

# 各家族默认半衰期（分钟）。标注「待标定」：调研附录指出缺实证数值，v0.1 取可调常数。
FAMILY_HALF_LIFE_MIN: dict[str, float] = {
    "anger": 12.0,
    "fear": 8.0,
    "disgust": 15.0,
    "sadness": 45.0,          # 悲伤衰减更慢
    "grief": 240.0,           # 哀恸小时级
    "joy": 10.0,
    "self_conscious": 20.0,   # 羞耻余韵长于愤怒
    "social_moral": 15.0,
    "love": 25.0,
    "epistemic": 5.0,
    "aesthetic": 12.0,
    "kama_muta": 1.5,         # 被感动 1–2 分钟内（调研 §1.5.8）
    "prospect": 10.0,
}


@dataclass
class EmotionEpisode:
    """一次情绪发作（类别软激活；intensity 0–1）。"""

    category: str
    intensity: float
    onset_min: float = 0.0
    half_life_min: float = 10.0
    family: str = "composite"
    # wanting/liking 双通道标记（调研 §6.3.6；v0.1 类别级标记）
    wanting: float = 0.0
    liking: float = 0.0

    def decayed(self, now_min: float) -> float:
        return self.intensity * math.pow(
            0.5, max(0.0, now_min - self.onset_min) / max(self.half_life_min, 1e-6)
        )


@dataclass
class MoodState:
    """心情层：情绪的慢速指数滑动平均（时间常数小时级）。"""

    valence: float = 0.0    # -1–1
    arousal: float = 0.15   # 0–1 基线微正

    def update(self, valence: float, arousal: float, weight: float) -> None:
        """慢速 EMA：weight 为本次事件的慢速权重（≪1，防单事件翻转心情，R-DYN-01）。"""
        w = min(max(weight, 0.0), 0.5)
        self.valence = (1 - w) * self.valence + w * valence
        self.arousal = (1 - w) * self.arousal + w * arousal


@dataclass
class MemoryTrace:
    """峰终记忆评分（R-DYN-02）：只记峰值与终值，时长不入公式。"""

    peak_valence: float = 0.0     # 会话内达到的最好（或最差）效价
    peak_intensity: float = 0.0   # 最强发作强度
    end_valence: float = 0.0      # 最后一次事件的效价
    events: int = 0

    @property
    def remembered_valence(self) -> float:
        """记忆评分 ≈ (峰 + 终)/2（等权为模型惯例而非估计值：Kahneman, Fredrickson,
        Schreiber & Redelmeier 1993, Psych Science 4:401-405；Redelmeier, Katz & Kahneman
        2003, Pain 104:187-194 的 RCT 支持规则本身——峰值与末段均为显著预测因子、时长不预测，
        但未报告精确相对权重；2022 元分析 Alaybek et al., OBHDP 170:104149 支持峰终稳健）。"""
        return 0.5 * self.peak_valence + 0.5 * self.end_valence

    def observe(self, valence: float, intensity: float) -> None:
        """峰 = 强度最高时刻的（带符号）效价；并列强度时取更极端者；终值 = 最后事件。

        时长（事件数/分钟数）不进入 remembered_valence —— 时长忽视（R-DYN-02）。
        """
        self.events += 1
        is_new_peak = (
            self.events == 1
            or intensity > self.peak_intensity
            or (
                math.isclose(intensity, self.peak_intensity, rel_tol=1e-9, abs_tol=1e-9)
                and abs(valence) > abs(self.peak_valence)
            )
        )
        if is_new_peak:
            self.peak_valence = valence
            self.peak_intensity = intensity
        self.end_valence = valence


@dataclass
class AffectState:
    """完整情感状态（引擎在动力学模块中演化；本类只承载事实）。"""

    episodes: dict[str, EmotionEpisode] = field(default_factory=dict)  # category → 当前发作
    mood: MoodState = field(default_factory=MoodState)
    arousal_residue: float = 0.0            # 兴奋转移残余（Zillmann）
    now_min: float = 0.0                    # 会话内模拟钟
    habituation: dict[str, int] = field(default_factory=dict)   # stimulus_key → 重复次数
    rumination: float = 0.0                 # 未解决损失的反刍压力（意难平来源）
    memory: MemoryTrace = field(default_factory=MemoryTrace)
    regulation_depletion: float = 0.0       # 调节资源消耗（抑制代价累积）
    # 对特定对象的未偿情绪记账（R-APP-02/03 跨事件链）：violator→义愤强度、被羡慕者→恶意强度
    charges: dict[str, float] = field(default_factory=dict)
    # wanting/liking 双池（§6.3.6 双通道独立环路）：wanting 池衰减更慢——「刷完空虚」的不对称基础
    wanting_pool: float = 0.0
    liking_pool: float = 0.0

    def activation(self, category: str) -> float:
        ep = self.episodes.get(category)
        return ep.decayed(self.now_min) if ep else 0.0

    def family_activation(self, family: str, catalog_family: dict[str, str]) -> float:
        """某家族当前残余总激活（catalog_family: category→family）。"""
        return sum(
            self.activation(cat)
            for cat, fam in catalog_family.items()
            if fam == family
        )

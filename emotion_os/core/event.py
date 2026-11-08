"""Event schema：结构化事件事实（架构合同 §4.3）。

事件携带客观事实；主观评价（SEC 维度）由 appraiser 结合 AgentProfile 计算——
这是「评价先行」原则（调研 §6.3.1）的接口体现：事件≠情绪，事件×主体目标/标准=情绪。
字段与调研章节对应：goal_impacts/expectancy_violation/probability/urgency/controllability/
reversibility/novelty/pleasantness ↔ §2.1 SEC 子维；moral/social/bond/aesthetic ↔ §2.5 E/G/F/I。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .types import EventCategory, Intent, TimeOrientation


@dataclass(frozen=True)
class MoralInfo:
    """道德/规范信息（调研 §2.5 E 违范类）。virtue=True 表示见证美德（§3.3 崇高/钦佩）。"""

    severity: float = 0.5          # 违范或美德的程度 0–1
    victim: str = "self"           # 受害方（"self" 或他者 id）
    violator: str | None = None    # 违规方
    virtue: bool = False           # True=美德见证；False=违范


@dataclass(frozen=True)
class SocialInfo:
    """社会比较信息（调研 §2.5 G、§3.3 van de Ven 羡慕分流）。"""

    direction: str = "up"          # "up"=他人优于己 / "down"=他人劣于己
    deservedness: float = 0.5      # 对方结果的应得感 0–1（良性/恶意羡慕分流键）
    domain: str = "status"


@dataclass(frozen=True)
class BondInfo:
    """联结变化（调研 §2.5 F、§1.5.8 kama muta 骤增触发）。"""

    delta: float = 0.5             # 关系变化幅度 0–1（正=增强；断裂用 break_up）
    sudden: bool = True            # 骤增（True 触发 kama muta；False 渐进→温情）
    break_up: bool = False         # 拒绝/背叛/排斥（社会疼痛，§1.5.5）
    romantic: bool = False         # 浪漫语境（心动）


@dataclass(frozen=True)
class AestheticInfo:
    """审美信息（调研 §3.3 审美族、§1.5.9 敬畏 = vastness + accommodation）。"""

    vastness: float = 0.0          # 巨大感→敬畏
    beauty: float = 0.0            # 形式美→美感
    skill: float = 0.0             # 卓越能力→钦佩
    virtue: float = 0.0            # 美德见证→崇高（与 MoralInfo.virtue 互补：这里指旁观见证）


@dataclass(frozen=True)
class Event:
    """一次情绪诱发事件的结构化表示。

    只声明事实；goal_relevance/control 等主观量由评价器结合主体目标计算。
    safety_frame/fictionality 是「后果真实性」参数（调研 §6.3.4 安全框架开关）。
    """

    category: EventCategory
    description: str = ""
    affects: str = "self"                      # 受影响者："self"/他者id/"group:x"/"fictional:x"
    caused_by: str | None = None               # 行为者（归因键；None=无人/情境）
    intent: Intent = Intent.UNKNOWN

    # SEC① 相关性输入
    goal_impacts: Mapping[str, float] = field(default_factory=dict)  # goal_id → 促/阻 -1–+1
    novelty: float = 0.0                       # 新异性/突发性 0–1
    pleasantness: float = 0.0                  # 内在愉悦度 -1–1

    # SEC② 含义输入
    expectancy_violation: float = 0.0          # 期望违背幅度 0–1（RPE，§1.5.3）
    probability: float = 1.0                   # 结果概率（<1 为前景/悬念）
    urgency: float = 0.0                       # 紧迫/临近 0–1（§4.1）
    reversibility: float = 1.0                 # 1=可逆 … 0=不可逆

    # SEC③ 应对输入（None=由评价器结合主体力量计算）
    control_hint: float | None = None

    # 结构化子信息
    moral: MoralInfo | None = None
    social: SocialInfo | None = None
    bond: BondInfo | None = None
    aesthetic: AestheticInfo | None = None

    # 复合/领域特化标志
    justice_restored: float = 0.0              # 违规者受罚程度 0–1（解气前置之一，§2.5 E）
    justice_target: str | None = None          # 受罚方 id（R-APP-02：须匹配先前违规者才产生解气）
    prior_threat_resolved: bool = False        # 先前威胁解除（解脱，§2.3）
    prior_adversity_resolved: bool = False     # 先前逆境被战胜（fiero，§5.3）
    effort: float = 0.0                        # 主体投入的努力 0–1（骄傲/fiero 权重）
    insight: bool = False                      # 理解发生（aha，§2.5 H）

    # 安全框架与虚构（§6.3.4）
    safety_frame: float = 1.0                  # 1=确认安全/虚构 … 0=真实后果
    fictionality: float = 0.0                  # 0=真实 … 1=虚构

    # 横切维度（§2.5）
    time_orientation: TimeOrientation = TimeOrientation.PRESENT
    stimulus_key: str | None = None            # 习惯化键（重复刺激衰减，§4.4）

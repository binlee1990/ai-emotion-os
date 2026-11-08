"""共享类型：枚举与基础值对象。来源标注引用 research/人类情绪全景调研.md 章节。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EventCategory(str, Enum):
    """事件大类 A–K（调研 §2.5 完备清单；每个具体事件都能归入 ≥1 类）。"""

    LOSS = "A_loss"                    # 损失：目标对象不可逆失去
    THREAT = "B_threat"                # 威胁：潜在伤害预告（尚未发生）
    FRUSTRATION = "C_frustration"      # 阻碍/挫折：目标追求被阻挡
    ACHIEVEMENT = "D_achievement"      # 获得/达成
    VIOLATION = "E_violation"          # 违范/冒犯
    BOND = "F_bond"                    # 联结：共享关系的发生/增强/修复/断裂
    COMPARISON = "G_comparison"        # 比较/地位
    NOVELTY = "H_novelty"              # 新奇/认识：信息缺口、意外、理解发生
    AESTHETIC = "I_aesthetic"          # 审美
    BODY = "J_body"                    # 身体状态
    FICTION = "K_fiction"              # 想象/虚构


class Intent(str, Enum):
    """归因故意性（调研 §4.1 归因清晰度：故意归因 → 愤怒放大）。"""

    NONE = "none"
    ACCIDENTAL = "accidental"
    DELIBERATE = "deliberate"
    UNKNOWN = "unknown"


class TimeOrientation(str, Enum):
    """时间指向（调研 §2.5 横切维度：过去→后悔/怀念；未来→希望/焦虑）。"""

    PAST = "past"
    PRESENT = "present"
    FUTURE = "future"


class OCCBranch(str, Enum):
    """OCC 三分支判定（调研 §2.3：事件后果/前景/行为者行为/对象属性 + 他人际遇）。"""

    CONSEQUENCES = "consequences"          # 福利：快乐/悲伤
    PROSPECTS = "prospects"                # 前景：希望/恐惧→满足/解脱/失望
    AGENCY_SELF = "agency_self"            # 自己行为：骄傲/羞耻
    AGENCY_OTHER = "agency_other"          # 他人行为：钦佩/谴责（含道德见证）
    ATTRACTION = "attraction"              # 对象属性：爱/恨
    FORTUNES_OF_OTHERS = "fortunes"        # 他人际遇：为他高兴/幸灾乐祸/怜悯
    BOND = "bond"                          # 联结变化（OCC 之外，调研 F 类）
    SOCIAL_COMPARISON = "comparison"       # 社会比较（OCC 之外，调研 G 类）
    EPISTEMIC = "epistemic"                # 认识性（OCC 之外，调研 H 类）
    AESTHETIC = "aesthetic_dim"            # 审美（调研 I 类）
    JUSTICE = "justice"                    # 违规受罚→解气（调研 E 类特化）


@dataclass(frozen=True)
class Personality:
    """Big Five 人格参数 0–1（调研 §4.2：神经质放大负性、感觉寻求预测恐惧享受等）。"""

    neuroticism: float = 0.5
    extraversion: float = 0.5
    openness: float = 0.5
    agreeableness: float = 0.5
    conscientiousness: float = 0.5


@dataclass(frozen=True)
class StateFactors:
    """当前状态因子（调研 §4.2：睡眠剥夺放大杏仁核反应 ~60% 等）。"""

    sleep_deprivation: float = 0.0   # 0–1
    fatigue: float = 0.0             # 0–1
    stress_baseline: float = 0.0     # 慢性应激（皮质醇基线）0–1


@dataclass(frozen=True)
class Goal:
    """主体目标（GAMYGDALA 式目标注解接口；importance 参与相关性权重）。"""

    goal_id: str
    description: str = ""
    importance: float = 0.5          # 0–1 目标重要性（强度因子，调研 §4.1）


@dataclass
class HabituationEntry:
    """习惯化/敏感化计数（调研 §4.4：重复暴露衰减 vs 创伤线索增强）。"""

    count: int = 0
    multiplier: float = 1.0

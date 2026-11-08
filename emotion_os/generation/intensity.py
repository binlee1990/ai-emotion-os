"""强度模型：事件因子 × 个体因子 × 状态因子的乘法结构（调研 §4.1–§4.3、§6.3.3；R-INT-01/02）。

- 零点性质：goal_relevance=0 → 一切激活为 0（相关性为零则无情绪，调研 §1.1）。
- 损失厌恶：负向阻碍的强度乘 λ≈2（丢 100 的痛 ≈ 得 200 的乐）。λ=2.25 的拟合出自
  Tversky & Kahneman **1992**（累积前景理论，非 1979 原始前景理论——后者提出概念未给该值）。
- 个体因子：神经质放大负性、外向放大正性、共情放大替代性、开放性放大审美、
  感觉寻求放大恐惧享受（调研 §4.2）。
- 状态因子：睡眠剥夺/疲劳/慢性应激放大负性；唤醒残余放大高唤醒类别（兴奋转移 §1.5.2）。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..appraiser import AppraisalResult
from ..core.agent import AgentProfile
from ..core.state import AffectState
from .catalog import CATALOG

# 待标定常数（调研附录：缺实证数值，v0.1 取可调常数）
# λ 出处（2026-11 复审核验）：
# - Tversky & Kahneman 1992 (J Risk Uncertainty 5:297-323, doi:10.1007/BF00122574) 拟合 2.25
#   （n=25 研究生、假设性小额赌注）；
# - Walasek, Mullett & Stewart 2024 (J Econ Psychol, 风险情境元分析，约 17 项研究)：≈1.31 [1.10,1.53]；
# - Neumann & Böckenholt 2014 (33 项研究/109 估计，品牌选择情境，经 Walasek 2024 转引)：1.49–1.73；
# - Brown, Imai, Vieider & Camerer 2024 (J Econ Lit, 充分激励实验的汇总均值)：1.955 [1.82,2.10]。
# 取 2.0：与 Brown et al. 2024 的激励实验汇总最接近，落在各元分析区间上段；非任何单一文献精确值。
LOSS_AVERSION = 2.0          # 损失厌恶系数（R-INT-02）
RESIDUE_GAIN = 0.4           # 唤醒残余对高唤醒类别的加成（兴奋转移）
STATE_AMP_SLEEP = 0.6        # 睡眠剥夺放大（杏仁核反应 +~60%，调研 §4.2）


def _b01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass(frozen=True)
class _Factors:
    individual: float
    state: float
    event_side: float


def individual_factor(category_id: str, r: AppraisalResult, agent: AgentProfile) -> float:
    cat = CATALOG[category_id]
    p = agent.personality
    f = 1.0
    if cat.valence < -0.1:
        f *= 0.6 + 0.8 * p.neuroticism          # 神经质放大负性
    elif cat.valence > 0.1:
        f *= 0.6 + 0.8 * p.extraversion         # 外向放大正性
    if r.affects not in ("self", agent.agent_id):
        f *= 0.5 + 0.7 * agent.empathic_trait   # 替代性情绪经共情传导
    if cat.family == "aesthetic":
        f *= 0.7 + 0.6 * p.openness
    if category_id == "fear_enjoyment":
        f *= 0.6 + 0.8 * agent.sensation_seeking
    return f


def state_factor(category_id: str, r: AppraisalResult, agent: AgentProfile, state: AffectState) -> float:
    cat = CATALOG[category_id]
    f = 1.0
    if cat.valence < -0.1:
        f *= 1.0 + STATE_AMP_SLEEP * agent.state.sleep_deprivation \
             + 0.3 * agent.state.fatigue + 0.5 * agent.state.stress_baseline
    if cat.arousal > 0.6:
        f *= 1.0 + RESIDUE_GAIN * state.arousal_residue   # 兴奋转移叠加
    return f


def event_factor(r: AppraisalResult) -> float:
    """事件侧共性因子：期望违背放大（RPE，§1.5.3）+ 受累目标数微增。"""
    ev = 0.65 + 0.7 * r.expectancy_violation
    goals = 1.0 + 0.1 * max(0, r.n_goals_affected - 1)
    return ev * goals


def episode_intensity(
    raw: float, category_id: str, r: AppraisalResult,
    agent: AgentProfile, state: AffectState,
) -> float:
    """R-INT-01：相关性为零 → 强度为零（无论模式多匹配）。"""
    if r.goal_relevance <= 0.02:
        return 0.0
    cat = CATALOG[category_id]
    value = raw
    # 损失厌恶（R-INT-02）：负效价类别 × 阻碍事件 → 乘 λ
    if cat.valence < -0.1 and r.conduciveness < -0.05:
        value *= LOSS_AVERSION
    value *= individual_factor(category_id, r, agent)
    value *= state_factor(category_id, r, agent, state)
    value *= event_factor(r)
    return _b01(value)

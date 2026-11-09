"""评价→类别激活映射：调研 §6.2 主对照表的可计算实现。

两遍扫描：
  pass1 家族评价器——纯评价配置驱动（本事件）；
  pass2 复合评价器——依赖 pass1 结果或先前状态（解气/爽/破防/意难平/倒U享受等跨事件机制）。
激活为 0–1 原始强度；个体/状态/不对称因子在 intensity 模块统一施加（乘法结构）。
"""
from __future__ import annotations

from ..appraiser import AppraisalResult
from ..core.agent import AgentProfile
from ..core.event import Event
from ..core.state import AffectState
from .catalog import CATALOG

Acts = dict[str, float]


def _b01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _tent(x: float, peak: float) -> float:
    """分段线性倒 U：peak 处最大，两侧线性衰减（调研 §1.5.4 享受峰值「恰在不能忍受之下一档」）。"""
    x = _b01(x)
    if x <= peak:
        return x / max(peak, 1e-6)
    return max(0.0, 1.0 - (x - peak) / max(1.0 - peak, 1e-6))


# 最适恐惧点：Andersen et al. 2020 (Psychological Science 31:1497-1510, doi:10.1177/0956797620972116)
# 鬼屋研究确证享受-恐惧倒 U（地点层面二次项 β=-0.05, p=.014）。顶点由 OSF 开放数据
# (osf.io/43hzk) 复现拟合：enjoyment ~ fear + fear² + age + gender + motivation
# + (1|participant) + (1|location)（lme4 结构，statsmodels 复现），β_lin=0.671、
# β_quad=-0.044（论文报告 -0.05；mot/gender/age 效应均与论文一致）→ 顶点 Likert
# 7.55/9。换算假设：fear_engine = fear_likert/9（0–9 线性映射 0–1，「9=前所未有
# 的害怕」≈ 引擎恐惧上限）。顶点 delta-method 95% CI=[5.32, 9.78]/9（引擎尺度
# [0.59, 1.09]）——点估计精度弱于两位小数所示；零依赖 OLS+位置固定效应回退口径
# 给 6.40/9=0.71，落在 CI 内。
# 复现脚本：scripts/fit_fear_enjoyment_peak.py。v0.2 自设 0.30 偏低（意味着几乎
# 不怕才最爽，与数据相反）；「最爱恰在不能忍受之下一档」的 Rozin et al. 2013
# (JDM 8:439-447) 序数表述与此一致（顶点在量表 84% 高位、极高处回落）。
FEAR_ENJOYMENT_PEAK = 0.84   # 最适恐惧点（Andersen 2020 OSF 数据拟合，7.55/9 换算；CI [0.59,1.09]）


# ---------------- pass 1：家族评价器 ----------------

def _anger(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    rel, cond = r.goal_relevance, r.conduciveness
    ob = max(0.0, -cond)
    ext_neg = max(0.0, -r.external_standard)      # 违范强度（他人/ witnessed）
    deliberate = 1.0 if r.deliberate_other else 0.0

    blocked = rel * min(1.0, ob + 0.7 * ext_neg)  # 家族底座：阻碍或违范
    # 愤怒：故意归因 + 高控制（觉得能改变→愤怒，§2.5 C）
    control_gate = _b01((r.control - 0.25) / 0.5)
    out["anger"] = blocked * (0.35 + 0.65 * deliberate) * control_gate
    out["frustration"] = rel * ob * 0.85 * (1.0 - 0.3 * deliberate)
    out["irritation"] = 0.5 * out["frustration"] * (1.0 - 0.5 * out["anger"])
    out["indignation"] = rel * ext_neg            # 义愤与控制无关（道德化愤怒）
    out["rage"] = max(0.0, out["anger"] - 0.75) * 3.0
    # 委屈：被错待（victim=self）+ 低控制无处申辩（§3.3 中文特有）
    if e.moral is not None and e.moral.victim == "self" and not e.moral.virtue:
        out["wei_yuan"] = rel * ext_neg * (1.0 - r.control) * 1.2
    # 憋屈：低控制下的持续愤怒-厌恶-悲伤混合（爽的前置状态，§3.3）
    pressure = max(ob, 0.8 * ext_neg)
    out["bie_qu"] = _b01(rel * pressure * (1.0 - r.control) * 1.3)
    # 屈辱（v0.9 Torres & Bergner 评价结构）：当众(public_setting) × 他人施加贬低
    # (victim=self) × 不应得(非自我理想违背——moral 为他人施加) × 无防御(低控制)。
    # 与委屈分流：wei_yuan 无需公开（被错待无处申辩），qu_ru 的扳机是当众地位降。
    # 他人施加由 moral.violator 承载；violator 缺失时与 wei_yuan 同款宽松（调用方守约）
    if (e.public_setting > 0.2 and e.moral is not None
            and e.moral.victim == "self" and not e.moral.virtue):
        pub_ramp = _b01((e.public_setting - 0.2) / 0.6)
        out["qu_ru"] = _b01(rel * ext_neg * pub_ramp * (1.0 - r.control) * 1.5)
    # 仇恨（v0.9 OCC 复合=悲+谴责）：不可逆伤害(reversibility 低) × 施加者 × 态度极负
    # (+先前记账加成)——区别 resentment：怒是对当下阻碍的发作，恨是对施加者的
    # 态度化持续；区别在于不可逆性与对象化。态度门为硬门：att≤-0.2 起坡、
    # -0.7 饱和（陌生/略好感的施加者不产仇恨——恨需要对象化的极负评价）
    if (e.moral is not None and e.moral.violator and not e.moral.virtue
            and e.reversibility < 0.35):
        att = a.attitude_toward(e.moral.violator)
        charge = s.charges.get(e.moral.violator, 0.0)
        att_gate = _b01((-att - 0.2) / 0.5)
        hate_base = rel * ext_neg * (1.0 - e.reversibility) * att_gate
        out["chou_hen"] = _b01(hate_base * (1.0 + 0.8 * min(1.0, charge)))


def _fear(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    threat = r.threat_level                      # rel×ob×prob
    prob = r.outcome_probability
    concrete = _b01((prob - 0.55) / 0.35)        # 概率→具体化
    uncertain = 1.0 - concrete                   # 不确定弥散 → 焦虑（§3.3 恐惧族）

    out["fear"] = threat * r.urgency * concrete * (1.0 - 0.4 * r.control)
    out["anxiety"] = threat * uncertain * (1.0 - 0.5 * r.control)
    out["dread"] = 0.5 * threat * (1.0 - r.urgency)
    out["startle"] = r.novelty * _b01(max(0.0, -r.conduciveness) + 0.3) * 0.8
    out["horror"] = out["fear"] * (0.25 + 0.75 * out.get("moral_disgust", 0.0)) * (1.0 - 0.5 * r.power)
    out["panic"] = out["fear"] * (1.0 - r.power) * _b01((r.urgency - 0.7) / 0.3)
    # 悬念 = 结果不确定×重要性×临近（调研 §4.3：不确定最大处在 p=0.5，故用 4p(1-p) 钟形；
    # threat_level 已含 p，这里改用不含 p 的阻碍底座，避免双重计入使峰值漂到 2/3）
    stakes = r.goal_relevance * max(0.0, -r.conduciveness)
    out["suspense"] = _b01(stakes * 4.0 * prob * (1.0 - prob)) * (0.4 + 0.6 * r.urgency)
    # 错失恐惧（v0.9 Przybylski 2013）：他人正在获益而自己缺席 × 窗口临近 ×
    # 不可及感（低控制放大）——relatedness 受挫的焦虑族变体
    if e.fomo > 0.05:
        out["fomo"] = _b01(r.goal_relevance * e.fomo * (0.5 + 0.5 * r.urgency) * (1.3 - 0.5 * r.control))


def _disgust(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    ext_neg = max(0.0, -r.external_standard)
    out["moral_disgust"] = r.goal_relevance * ext_neg
    att = a.attitude_toward(e.moral.violator) if e.moral and e.moral.violator else -0.3
    out["contempt"] = out["moral_disgust"] * _b01(0.3 - att)   # 向下看（对方低评价）
    # 核心厌恶：身体性负愉悦（J 类）
    if e.category.value == "J_body" and e.pleasantness < 0:
        out["disgust"] = r.goal_relevance * min(1.0, -e.pleasantness)


def _sadness(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    rel, cond = r.goal_relevance, r.conduciveness
    ob = max(0.0, -cond)
    irreversible = 1.0 - e.reversibility

    loss = rel * ob * (0.35 + 0.65 * irreversible)
    out["sadness"] = 0.9 * loss
    out["grief"] = loss * _b01((rel - 0.55) / 0.4) * irreversible
    out["despair"] = _b01(rel * ob * (1.0 - r.power) * (1.0 - r.adjustment))
    # 失望：先前期待落空（前景确认负结果）
    prior_hope = s.activation("hope") + s.activation("suspense")
    if r.outcome_probability >= 0.95 and ob > 0.15:
        out["disappointment"] = _b01(rel * ob * (0.45 + prior_hope))
    if e.bond is not None and e.bond.break_up:
        out["social_pain"] = rel * 0.95
        out["heartbreak"] = rel * 0.9
        out["loneliness"] = 0.4 * rel
    # 被排斥（v0.8 Williams 需求威胁模型）：来源可为群体/陌生人（无需既有关系）——
    # 反射性疼痛阶段：社会疼痛 + 孤独 + 被无视感（「存在被抹去」是定性访谈核心主题）
    if e.bond is not None and e.bond.excluded > 0.05:
        exc = e.bond.excluded
        out["social_pain"] = max(out.get("social_pain", 0.0), rel * exc * 0.95)
        out["loneliness"] = max(out.get("loneliness", 0.0), rel * exc * 0.6)
        # 无处申辩（低控制）时被无视感更强
        out["invisibility"] = rel * exc * (0.5 + 0.5 * (1.0 - r.control))
    # 共情疼痛：他者受苦 × 共情特质（dACC 共享回路，§1.5.5）
    if r.affects not in ("self",) and ob > 0.1:
        ep = r.goal_relevance * ob * a.empathic_trait
        out["empathic_pain"] = ep
        att = a.attitude_toward(r.affects)
        out["xin_teng"] = ep * max(0.0, att)     # 心疼 = 共情疼痛×爱


def _joy(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    rel, cond = r.goal_relevance, r.conduciveness
    pr = max(0.0, cond)
    gain = rel * pr

    out["joy"] = gain
    out["pleasure"] = _b01(max(0.0, r.pleasantness) * (0.4 + 0.6 * rel))
    out["contentment"] = 0.6 * gain * (1.0 - 0.7 * r.expectancy_violation)
    out["excitement"] = gain * (0.3 + 0.7 * r.novelty)
    out["ecstasy"] = _b01(gain * r.expectancy_violation * _b01((rel - 0.4) / 0.5) * 1.4)
    # fiero：战胜逆境的狂喜（努力×逆境解除，§5.3）
    if e.prior_adversity_resolved:
        out["fiero"] = _b01(e.effort * (0.45 + 0.55 * gain))
    # amusement：良性违规（违规+安全距离同时在场，§5.1 McGraw & Warren）
    ext_mag = abs(r.external_standard)
    out["amusement"] = _b01(ext_mag * r.novelty * r.safety_frame * 0.9)
    # 玩闹欢腾（v0.8 Panksepp PLAY）：社交加成 + 安全框架调制（真痛不是玩；
    # rough-and-tumble 的躯体-社交欢乐，amusement 之外的 PLAY 子集）——底座用
    # 相关性而非 goal 促进（玩闹本身即愉悦，不走目标得失通道）
    if e.play is not None:
        partnered = 1.0 if e.play.partnered else 0.55
        sf_ramp = _b01((r.safety_frame - 0.1) / 0.5)   # 破框架（真痛）→ 0
        out["play_joy"] = _b01(r.goal_relevance * e.play.level * partnered * sf_ramp * 1.6)
    # 他人际遇（§2.3 fortunes-of-others：方向由好恶决定）
    if r.affects not in ("self", a.agent_id):
        att = a.attitude_toward(r.affects)
        des = e.social.deservedness if e.social else 0.5
        # 纯比较事件的对方得/失由 direction 表达（无 goal_impacts 时 cond=0）
        other_gain = pr > 0.1 or (e.social is not None and e.social.direction == "up")
        other_loss = max(0.0, -cond) > 0.1 or (e.social is not None and e.social.direction == "down")
        if other_gain:   # 对方得好
            gain_mag = max(gain, 0.6 * r.goal_relevance)
            out["happy_for"] = gain_mag * max(0.0, att)
            out["resentment"] = gain_mag * max(0.0, -att) * 0.8
            if r.self_caused:
                out["naches"] = gain_mag * max(0.0, att)   # 我助之人成功→欣慰（Lazzaro people fun，§5.3）
        if other_loss:   # 对方失势
            out["gloating"] = r.goal_relevance * max(0.0, -att)
            # 应得感预测（§3.3）+ 先前恶意羡慕加成（van de Ven 2015 跨事件链，R-APP-03）
            charge = s.charges.get(r.affects, 0.0)
            out["schadenfreude"] = out["gloating"] * (0.4 + 0.6 * des) * (1.0 + 0.8 * charge)
            # 下行比较：优越（§6.2）；亲近者失势不优越
            out["superiority"] = 0.45 * r.goal_relevance * (0.3 + 0.7 * des) * _b01(0.4 - att)
            # 喜欢/中性的对方失势：同情为主；对方不应得时更强
            if att >= 0:
                out["sympathy"] = max(
                    out.get("sympathy", 0.0),
                    0.7 * r.goal_relevance * (1.0 - des) * (0.3 + 0.7 * max(0.0, att)),
                )
                # 自身情绪低落时的自利性安慰（下行比较的应对功能）
                if s.mood.valence < -0.1:
                    out["comfort"] = 0.5 * r.goal_relevance * max(0.0, -s.mood.valence)


def _self_conscious(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    if not r.self_caused:
        # 替代性尴尬：他人当众失误（对方不知情也尬，§3.3 Krach 2011）
        if r.affects not in ("self", a.agent_id) and r.novelty > 0.3 and e.moral is not None:
            out["vicarious_embarrassment"] = r.goal_relevance * r.novelty * a.empathic_trait * 0.9
        return
    int_neg = max(0.0, -r.internal_standard)
    int_pos = max(0.0, r.internal_standard)
    if int_neg > 0:
        victim_other = e.moral is not None and e.moral.victim not in ("self", None, "none")
        out["guilt"] = int_neg * r.goal_relevance * (0.8 if victim_other else 0.2)   # 他人受害→修复
        out["shame"] = int_neg * r.goal_relevance * (0.45 if not victim_other else 0.9)  # 自我意象→躲藏
        if e.moral is None or int_neg < 0.5:
            out["embarrassment"] = int_neg * r.novelty * 0.7
    if int_pos > 0 and max(0.0, r.conduciveness) > 0.05:
        out["pride"] = _b01(int_pos * (0.4 + 0.6 * e.effort))
        # 自负（v0.9 Tangney & Tracy hubristic 型）：自归因成就 × 低努力——归因到
        # 全局稳定自我（天赋/身份「我了不起」）的行为代理；与 pride（努力加权）
        # 天然分流：同一成就 effort 低则傲慢分量升、authentic 分量降。
        # effort>0.75 硬归零（高努力成就不产傲慢——两型是竞争构念而非叠加）
        out["ao_man"] = _b01(int_pos * max(0.0, r.conduciveness) * _b01(0.75 - e.effort) * 1.3)


def _social_moral(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    rel = r.goal_relevance
    # 感激：他人归因+促进+高价值（OCC 复合：钦佩+快乐）
    if r.causality_agent not in (None, "self") and max(0.0, r.conduciveness) > 0.1:
        att = a.attitude_toward(r.causality_agent or "")
        out["gratitude"] = _b01(rel * max(0.0, r.conduciveness) * (0.5 + 0.5 * max(0.0, att)))
    # 崇高：见证美德；钦佩：见证卓越技能（§3.3 Haidt）
    ext_pos = max(0.0, r.external_standard)
    if ext_pos > 0:
        out["elevation"] = rel * ext_pos * (0.6 + 0.4 * a.empathic_trait)
    if e.aesthetic is not None and e.aesthetic.skill > 0:
        out["admiration"] = rel * e.aesthetic.skill
    # 同情/慈悲
    ep = out.get("empathic_pain", 0.0)
    if ep > 0:
        out["sympathy"] = 0.8 * ep
        out["compassion"] = 0.7 * ep * (0.4 + 0.6 * r.power)
    # 羡慕分流（van de Ven：应得感×控制）
    if e.social is not None and e.social.direction == "up":
        env = rel * 0.9
        out["benign_envy"] = env * e.social.deservedness * (0.4 + 0.6 * r.control)
        out["malicious_envy"] = env * (1.0 - e.social.deservedness)
        if e.bond is not None and not e.bond.break_up and e.social.domain == "relationship":
            out["jealousy"] = env * (1.0 - e.social.deservedness) * 0.9  # 第三方威胁感情
    # 背叛：亲近者断联
    if e.bond is not None and e.bond.break_up and r.causality_agent not in (None, "self"):
        out["betrayal"] = rel * max(0.0, a.attitude_toward(r.causality_agent or ""))


def _love(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    if e.bond is None:
        return
    rel = r.goal_relevance
    d = e.bond.delta
    sudden = 1.0 if e.bond.sudden else 0.12      # 骤增才触发 kama muta（R-APP-05）
    out["kama_muta"] = _b01(rel * d * sudden * 1.5)
    out["tenderness"] = _b01(rel * d * (0.5 if e.bond.sudden else 1.0))
    out["attachment_warmth"] = _b01(rel * d * 0.55 * (1.0 - 0.5 * d))
    if e.bond.romantic:
        out["heart_flutter"] = _b01(d * (1.0 if e.bond.sudden else 0.4))
        out["romantic_passion"] = _b01(d * 0.8)
    # 渴望（v0.8 Panksepp LUST 欲望域）：wanting 主导的对象特异渴求——
    # 与心动区分（flutter=惊喜性吸引，craving=持续渴求）；残余 wanting 池放大
    # （异地思念的叠加：欲求缠身），持续暴露经状态累积而非事件幅度
    if e.bond.desire > 0.05:
        out["craving"] = _b01(rel * e.bond.desire * (0.9 + 0.5 * min(1.0, s.wanting_pool)) * 1.2)
    # 磕到了：目睹（虚构）关系升温（kama muta 粉丝文化变体，§3.3）
    if r.affects not in ("self", a.agent_id):
        out["ke_dao"] = _b01(rel * d * sudden * 1.2)
    # 集体欢腾：与群体同步的联结（涂尔干；调研 §5.8 宗教/仪式、§6.2 集体同步行）
    if r.affects.startswith("group:") and e.bond.sudden:
        out["collective_effervescence"] = _b01(rel * d * 1.2)


def _epistemic(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    nov = r.novelty
    ev = r.expectancy_violation
    out["surprise"] = ev * (1.0 if abs(r.conduciveness) < 0.3 else 0.75)   # 认知域违背为主
    out["shock"] = max(0.0, out["surprise"] - 0.7) * 3.0
    out["curiosity"] = nov * (0.5 + 0.5 * a.personality.openness) * (1.0 - 0.6 * out["surprise"])
    out["interest"] = out["curiosity"] * (0.5 + 0.5 * r.goal_relevance)
    if e.insight:
        out["aha"] = _b01(0.5 + 0.5 * nov)
    else:
        out["confusion"] = _b01(nov * 0.55 * (1.0 - min(1.0, abs(r.conduciveness) + abs(r.external_standard))))
    # 无聊：信息/价值枯竭（注意被占用但无价值，§3.3 Pekrun）
    if (r.goal_relevance > 0.05 and e.fomo < 0.05
            and abs(r.conduciveness) < 0.08 and nov < 0.15 and abs(r.pleasantness) < 0.2):
        # FOMO 在场时不出无聊（缺席焦虑是高投入状态，价值枯竭前提不成立）
        out["boredom"] = _b01(r.goal_relevance * 0.9 * (0.15 - nov) * 6.0)
    if e.aesthetic is not None:
        out["fascination"] = _b01(nov * max(e.aesthetic.beauty, e.aesthetic.skill))


def _aesthetic(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    if e.aesthetic is not None:
        rel = max(r.goal_relevance, 0.45)        # 审美：内在愉悦度主导，相关性退居次要（§3.3）
        out["beauty"] = _b01(rel * e.aesthetic.beauty)
        out["awe"] = _b01(rel * e.aesthetic.vastness * (0.7 + 0.3 * a.personality.openness) * (0.8 + 0.4 * r.novelty))
        # 崇拜（v0.9 Cowen 27 adoration）：对象奉献性吸引 × 对其态度——对象属性
        # 第三型（skill→钦佩 / virtue→崇高 / devotion→崇拜）；affects 即对象 id，
        # 指向自身时不出（自我崇拜语义未定义，抑制）
        if e.aesthetic.devotion > 0.05 and r.affects not in ("self", a.agent_id):
            att = a.attitude_toward(r.affects)
            out["chong_bai"] = _b01(rel * e.aesthetic.devotion * (0.5 + 0.5 * _b01(att)))
    if r.pleasantness > 0:
        if e.time_orientation.value == "past":
            out["nostalgia"] = _b01(0.7 * r.pleasantness)
        out["relaxation"] = _b01(0.6 * r.pleasantness * (1.0 - r.novelty))
        if e.category.value == "J_body":
            out["vitality"] = _b01(0.8 * r.pleasantness)
    # 物哀（v0.9 mono no aware）：美好在场 × 将逝觉察——无常的审美化哀愁。
    # 与怀旧分流：nostalgia=past 指向已逝之美的回望，wu_ai=当下觉察将逝
    # （樱花将落/最后一课/曲终人散）。美好是必要分量（乘法门，非地板）：纯损失
    # 性终结不出物哀（那 是悲伤/失望）；past 指向归怀旧，不双出
    if e.transience > 0.05 and e.time_orientation.value != "past":
        beauty_mag = max(e.aesthetic.beauty if e.aesthetic else 0.0, max(0.0, r.pleasantness))
        out["wu_ai"] = _b01(r.goal_relevance * e.transience * beauty_mag * 1.1)


def _prospect(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts) -> None:
    rel, cond = r.goal_relevance, r.conduciveness
    pr = max(0.0, cond)
    prob = r.outcome_probability
    if pr > 0.05 and prob < 0.95:
        out["hope"] = _b01(rel * pr * 2.0 * (1.0 - prob))
        out["anticipation"] = _b01(rel * pr * prob * 0.8)
    if cond < -0.1 and 0.1 < prob < 0.9:
        # 负向前景中的希望分量：悬念=恐惧+希望复合（§3.3、§2.5 B）——渴望更好结果
        out["hope"] = max(out.get("hope", 0.0), _b01(rel * (-cond) * (1.0 - prob) * 0.8))
    # 近失效应（v0.8 Clark 2009/2010）：差一点 → 不甘心 + 再试驱动（wanting 由
    # catalog 标记承载，池累积后可复合「上头」——差一点比差很多更想再来）
    if e.near_miss > 0.05:
        nm = e.near_miss
        out["bu_gan_xin"] = _b01(rel * nm * 0.9)
        out["disappointment"] = max(out.get("disappointment", 0.0), _b01(rel * nm * (0.4 + 0.4 * r.expectancy_violation)))
    if e.prior_threat_resolved:
        # 解脱强度 ∝ 先前威胁量（残余张力入式；§2.3、§4.3 兴奋转移）
        prior_tension = s.activation("suspense") + s.activation("fear") + s.activation("anxiety")
        out["relief"] = _b01(rel * (0.4 + 0.4 * r.expectancy_violation + 0.5 * min(1.0, prior_tension)))
    if e.time_orientation.value == "past" and r.self_caused and max(0.0, -cond) > 0.1 and e.reversibility > 0.3:
        out["regret"] = _b01(rel * max(0.0, -cond) * e.reversibility * 0.8)
    if pr > 0.1 and e.effort > 0.1:
        out["accomplishment"] = _b01(pr * (0.4 + 0.6 * e.effort) * rel)


# ---------------- pass 2：复合评价器（依赖 pass1 / 状态） ----------------

def _composites(r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState, out: Acts,
                pass1_keys: frozenset[str] | None = None) -> None:
    # 解气：先前对该违规者的义愤/愤怒 × 其受罚（R-APP-02：无前置义愤→0；罚错对象→0）
    if e.justice_restored > 0.05:
        target_charge = s.charges.get(e.justice_target, 0.0) if e.justice_target else max(
            s.activation("indignation"), s.activation("anger"), s.activation("wei_yuan")
        )
        out["jie_qi"] = _b01(e.justice_restored * min(1.0, 1.3 * target_charge))
        if out["jie_qi"] > 0 and r.affects not in ("self", a.agent_id):
            # 正义恢复+为他高兴（fortunes-of-others：仅当受益的是他者；OCC 语义）
            out["happy_for"] = max(out.get("happy_for", 0.0), 0.6 * out["jie_qi"])
    # 爽：憋屈释放 ×（fiero/解气/解脱/大收获）——对比增强（§5.4）
    suppressed = s.activation("bie_qu")
    if suppressed > 0.25:
        release = max(out.get("fiero", 0.0), out.get("jie_qi", 0.0), out.get("relief", 0.0),
                      1.0 if out.get("joy", 0.0) > 0.6 else 0.0)
        out["shuang"] = _b01(suppressed * 1.4 * release)
    # 破防：感动/悲伤/委屈的强形式（心理防御被击穿，§3.3）
    for src in ("kama_muta", "sadness", "wei_yuan", "grief"):
        m = out.get(src, 0.0)
        if m > 0.75:
            out["po_fang"] = max(out.get("po_fang", 0.0), _b01((m - 0.7) * 3.3))
    # 恐惧享受：安全框架内的倒 U（R-APP-04）；安全框架平滑过渡（0.2–0.8 线性坡，待标定）
    if out.get("fear", 0.0) > 0.05:
        sf_ramp = _b01((r.safety_frame - 0.2) / 0.6)
        out["fear_enjoyment"] = (
            _tent(out["fear"], FEAR_ENJOYMENT_PEAK)
            * sf_ramp
            * (0.6 + 0.4 * a.sensation_seeking)
        )
    # 颤栗快感 chills：审美高峰 × 预期张力解决（§5.5：chills 常在预期解决处）
    beauty_peak = max(out.get("beauty", 0.0), out.get("awe", 0.0))
    prior_tension = s.activation("suspense") + s.activation("anticipation") + s.activation("fear")
    if beauty_peak > 0.35 and prior_tension > 0.15:
        out["chills"] = _b01(beauty_peak * (0.35 + 0.65 * min(1.0, prior_tension)))
    # 上头：wanting 池显著压过 liking 池（wanting≠liking 的行为学标记，§1.5.1）
    if s.wanting_pool > 0.2:
        ratio = s.wanting_pool / (s.liking_pool + 0.2)
        if ratio > 1.5:
            out["shang_tou"] = _b01((ratio - 1.5) * 0.6)
    # 麻了：情绪过载后的钝化（调研 §3.3：习惯化或调节耗竭的表达）——
    # 负性心境 + 调节资源耗竭 + 高唤醒残余共同触发
    overload = (max(0.0, -s.mood.valence)) * s.regulation_depletion * (0.5 + 0.5 * s.arousal_residue)
    if overload > 0.15:
        out["numb"] = _b01(overload * 1.5)
    # 意难平：反刍压力的反思性激活（dynamics 维护 rumination）
    if s.rumination > 0.15:
        out["yi_nan_ping"] = _b01(0.55 * s.rumination)
    # 矛盾（v0.8 目标冲突/混合情绪）：正负并存 → 并存紧张而非相互抵消（Larsen 2001）。
    # 双通道检测：(a) 评价输入层——正负 goal_impacts 双侧显著即冲突（按目标重要性
    # 加权，与 appraiser 的 conduciveness 同一口径——对无该目标的主体不得报冲突；
    # 等强对消时 conduciveness=0、输出层无从感正负，输入层结构是唯一信号）；
    # (b) 输出层——家族评价器直出（pass1）的正负类别激活均过阈（0.35，防单侧主导
    # 误报）；两通道取 max，平衡度加权（正负等强时最「撕扯」）。排除集：
    # 低唤醒背景态（boredom/numb/confusion——负效价是「无事件」的钝化，「温情+无聊」
    # 不是矛盾）与同事件派生复合类（po_fang/shuang/jie_qi 等 pass2 产物——由本事件
    # 其它类别点燃，其效价不构成与正侧的对立：破防≠撕扯、解气+喜悦≠矛盾——
    # 只统计 pass1_keys 保证此性质，黑名单不可枚举）
    amb_input = 0.0
    pos_imp = sum(
        d * a.goal_importance(g)
        for g, d in e.goal_impacts.items()
        if d > 0.15 and a.goal_importance(g) > 0.05
    )
    neg_imp = sum(
        -d * a.goal_importance(g)
        for g, d in e.goal_impacts.items()
        if d < -0.15 and a.goal_importance(g) > 0.05
    )
    if pos_imp > 0.15 and neg_imp > 0.15:
        lo_i, hi_i = min(pos_imp, neg_imp), max(pos_imp, neg_imp)
        amb_input = r.goal_relevance * (lo_i / hi_i) * 0.9
    _bg = {"boredom", "numb", "confusion"}
    p1 = pass1_keys if pass1_keys is not None else frozenset(out)
    pos_max = max((v for k, v in out.items() if k in p1 and k not in _bg and CATALOG[k].valence > 0.2), default=0.0)
    neg_max = max((v for k, v in out.items() if k in p1 and k not in _bg and CATALOG[k].valence < -0.2), default=0.0)
    amb_output = 0.0
    if pos_max > 0.35 and neg_max > 0.35:
        lo_o, hi_o = min(pos_max, neg_max), max(pos_max, neg_max)
        amb_output = lo_o * (0.5 + 0.5 * lo_o / hi_o) * 1.6
    out["ambivalence"] = _b01(max(amb_input, amb_output))
    # 排斥的反思性路径（v0.8 Williams）：疼痛之后按应对资源分流——力量感低
    # （承不住）+ 排斥重 → 外化攻击（反社会路径：控制需求受威胁的补偿性反应）；
    # 力量感高者走亲社会路径（求重新接纳，已由 loneliness 倾向承载）
    if e.bond is not None and e.bond.excluded > 0.4 and r.power < 0.4:
        out["anger"] = max(out.get("anger", 0.0), _b01(r.goal_relevance * e.bond.excluded * (1.0 - r.power) * 1.2))
    # 自怜（v0.9 HUMAINE）：委屈 × 无人看见（被无视/孤独）——受害感+孤立感的
    # 自我沉溺；与 wei_yuan 分流：委屈是状态，自怜是对状态的自我聚焦放大
    wy = out.get("wei_yuan", 0.0)
    if wy > 0.3:
        unsupport = max(out.get("invisibility", 0.0), 0.8 * out.get("loneliness", 0.0))
        if unsupport > 0.15:
            out["zi_lian"] = _b01(wy * (0.4 + 0.6 * unsupport) * (1.0 - r.control) * 1.35)


FAMILY_EVALUATORS = (
    _anger, _fear, _disgust, _sadness, _joy,
    _self_conscious, _social_moral, _love, _epistemic, _aesthetic, _prospect,
)


def evaluate_activations(
    r: AppraisalResult, e: Event, a: AgentProfile, s: AffectState
) -> Acts:
    """主入口：评价结果 → {category: 原始激活}。"""
    out: Acts = {}
    for fn in FAMILY_EVALUATORS:
        fn(r, e, a, s, out)
    pass1_keys = frozenset(out)   # 家族评价器直出（ambivalence 输出层只认原始并存）
    _composites(r, e, a, s, out, pass1_keys=pass1_keys)
    return {k: v for k, v in out.items() if v > 0.02}

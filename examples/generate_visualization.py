# -*- coding: utf-8 -*-
"""生成 ai-emotion-os 整体可视化页面：引擎真实输出 → 自包含 HTML。

数据全部来自引擎真实调用（不手写编造数值）：
  1) 管线解剖：单事件五阶段中间产物（评价向量/激活/动力学/表达）
  2) 情绪弧线：8 事件叙事（demo_story 同弧线）逐事件词×强度/4D/心情/峰终
  3) 语域对照：最终状态 formal/neutral/colloquial 三档
  4) 倒 U 曲线：fear_enjoyment = tent(fear,0.84)×sf×ss 引擎真实函数值扫描
  5) 峰终记忆：MemoryTrace 轨迹
模板 examples/visual_template.html 的 __DATA__ 占位符替换 → docs/visualization.html。

运行：python examples/generate_visualization.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Intent
    from emotion_os.core.event import AestheticInfo, BondInfo, MoralInfo, SocialInfo
    from emotion_os.generation.catalog import CATALOG, HALF_LIFE_BY_CATEGORY
    from emotion_os.generation.mapping import FEAR_ENJOYMENT_PEAK, _tent
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Intent
    from emotion_os.core.event import AestheticInfo, BondInfo, MoralInfo, SocialInfo
    from emotion_os.generation.catalog import CATALOG, HALF_LIFE_BY_CATEGORY
    from emotion_os.generation.mapping import FEAR_ENJOYMENT_PEAK, _tent

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_story import STORY  # 同一弧线，数据一致

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "visualization.html"
TEMPLATE = Path(__file__).resolve().parent / "visual_template.html"

SS = 0.6  # 与 demo/场景测试一致的中档感觉寻求

# ---------------- 事件类型档案（v2）：元信息 + 代表事件 + 变体 ----------------
# 展示层内容（徽标/例子/关联映射）为手写标注；全部数值由引擎真算（下方 _dissect/_fire）。

INTENT_ZH = {Intent.DELIBERATE: "故意", Intent.ACCIDENTAL: "无意",
             Intent.UNKNOWN: "不明", Intent.NONE: "无"}

_EVT_META = {
    "A_loss": {"label": "失去", "zh": "损失", "def": "目标对象不可逆失去",
               "valence": "neg", "attr": "命运·无行为者",
               "knob": "对亲密联结的冲击",
               "tests": [["test_be_peak_end.py", "BE 结局意难平：高峰+负终值的记忆结构"]],
               "rules": [["R-INT-02", "损失厌恶：同幅度损失强度约为收益 2 倍"],
                         ["R-DYN-02", "峰终记忆：评分≈峰值+结尾，时长不计"]]},
    "B_threat": {"label": "遇威胁", "zh": "威胁", "def": "潜在伤害预告（尚未发生）",
                 "valence": "neg", "attr": "情境·概率未定",
                 "knob": "对牵挂之人的威胁程度",
                 "tests": [["test_suspense.py", "悬念钟形：不确定最大在 p=0.5"],
                           ["test_horror_inverted_u.py", "安全框架内恐惧→享受倒 U"]],
                 "rules": [["R-INT-01", "乘法结构：目标相关性为零则零情绪"]]},
    "C_frustration": {"label": "受阻", "zh": "阻碍/挫折", "def": "目标追求被阻挡",
                      "valence": "neg", "attr": "他人·归因不明",
                      "knob": "对自尊目标的阻碍",
                      "tests": [["test_shortdrama_loop.py", "憋屈铺垫→释放的爽感结构"]],
                      "rules": [["R-APP-01", "愤怒配置：低控制时转向恐惧/悲伤（此处为憋屈）"]]},
    "D_achievement": {"label": "有成就", "zh": "获得/达成", "def": "目标实现、收获与胜利",
                      "valence": "pos", "attr": "自己·努力归因",
                      "knob": "对自尊目标的促进",
                      "tests": [["test_shortdrama_loop.py", "反杀打脸的 fiero×爽感"],
                                ["test_sport_social.py", "压哨绝杀：fiero×兴奋转移"]],
                      "rules": [["R-DYN-03", "兴奋转移：绝杀=fiero×前置唤醒残余"]]},
    "E_violation": {"label": "被冒犯", "zh": "违范/冒犯", "def": "他人违反规范，侵犯自身或所在群体的利益",
                    "valence": "neg", "attr": "他人·故意归因",
                    "knob": "对自尊目标的冲击",
                    "tests": [["test_face_slap.py", "打脸三连：憋屈→解气→罚错对象内疚"]],
                    "rules": [["R-APP-01", "愤怒配置：高相关+他人故意+阻碍+高控制→愤怒"],
                              ["R-APP-02", "解气生成：先前义愤+相称惩罚→解气"]]},
    "F_bond": {"label": "关系变动", "zh": "联结", "def": "共享关系的发生/增强/修复/断裂",
               "valence": "dual", "attr": "他人·善意或决裂",
               "knob": "关系变化（负=决裂，正=骤增）",
               "tests": [["test_reunion.py", "骤增触发 kama muta，渐增只生温情"]],
               "rules": [["R-APP-05", "kama muta：共享关系骤增才触发，渐增不触发"]]},
    "G_comparison": {"label": "与人比较", "zh": "比较/地位", "def": "与他人对照下的自我定位变化",
                     "valence": "dual", "attr": "无行为者·纯比较",
                     "knob": "比较方向（负=对方占优）",
                     "tests": [["test_envy_split.py", "羡慕分流：应得感×控制感→良性/恶意"]],
                     "rules": [["R-APP-03", "羡慕分流：高应得→向上努力；低应得→拉倒对方"]]},
    "H_novelty": {"label": "遇新奇", "zh": "新奇/认识", "def": "信息缺口、意外、理解发生",
                  "valence": "dual", "attr": "无行为者·信息事件",
                  "knob": "信息增益（负=信息枯竭）",
                  "tests": [["test_rpe.py", "预期违背与反转的激活结构"]],
                  "rules": [["R-INT-01", "乘法结构：认识性需要基线相关由开放性调制"]]},
    "I_aesthetic": {"label": "审美", "zh": "审美", "def": "面对美、浩瀚与卓越的形式体验",
                    "valence": "pos", "attr": "无行为者·对象属性",
                    "knob": "美感与浩瀚感",
                    "tests": [["test_music.py", "chills 颤栗：审美高峰×预期张力解决"]],
                    "rules": []},
    "J_body": {"label": "躯体感受", "zh": "身体状态", "def": "躯体状态变化引发的内在感受",
               "valence": "dual", "attr": "自己·身体状态",
               "knob": "躯体感受（负=不适）",
               "tests": [["test_sport_social.py", "运动场景：跑者高潮/躯体活力"]],
               "rules": []},
    "K_fiction": {"label": "虚构剧情", "zh": "想象/虚构", "def": "虚构框架内代入经历的一切",
                  "valence": "dual", "attr": "虚构·代入",
                  "knob": "剧情对牵挂角色的冲击",
                  "tests": [["test_horror_inverted_u.py", "安全框架开关：破损→享受归零"]],
                  "rules": [["R-APP-04", "安全框架倒 U：框架内恐惧→享受；破损→纯恐惧"]]},
}


def _r(x, n=2):
    return None if x is None else round(float(x), n)


def _extras(ev: Event) -> str:
    """事件结构化子信息一瞥（手写格式化，字段值真实）。"""
    parts = []
    if ev.moral is not None:
        kind = "美德" if ev.moral.virtue else "违范"
        s = f"moral[{kind}] {ev.moral.severity:g} victim={ev.moral.victim}"
        if ev.moral.violator:
            s += f" violator={ev.moral.violator}"
        parts.append(s)
    if ev.bond is not None:
        s = f"bond Δ{ev.bond.delta:g}"
        if ev.bond.sudden:
            s += " 骤增"
        if ev.bond.break_up:
            s += " 决裂"
        if ev.bond.romantic:
            s += " 浪漫"
        parts.append(s)
    if ev.social is not None:
        parts.append(f"social {'上行' if ev.social.direction == 'up' else '下行'} "
                     f"应得感={ev.social.deservedness:g}")
    if ev.aesthetic is not None:
        a = ev.aesthetic
        seg = [f"{k}{v:g}" for k, v in (("浩瀚", a.vastness), ("形式美", a.beauty),
                                         ("技艺", a.skill), ("美德", a.virtue)) if v > 0]
        if seg:
            parts.append("aesthetic " + "/".join(seg))
    if ev.reversibility < 1.0:
        parts.append(f"可逆性={ev.reversibility:g}")
    if ev.effort > 0.0:
        parts.append(f"努力={ev.effort:g}")
    if ev.justice_restored > 0.0:
        parts.append(f"正义恢复={ev.justice_restored:g}→{ev.justice_target}")
    if ev.prior_adversity_resolved:
        parts.append("逆境战胜")
    if ev.insight:
        parts.append("理解发生")
    if ev.fictionality > 0.0:
        parts.append(f"虚构度={ev.fictionality:g} 安全框架={ev.safety_frame:g}")
    return " · ".join(parts) or "—"


def _dissect(agent: AgentProfile, ev: Event, title: str) -> dict:
    """单事件孤立真算：五阶段中间产物（事件/评价/激活/动力学余波/表达）。"""
    eng = EmotionEngine(agent)
    r = eng.process(ev, dt_minutes=1.0)
    ap = r.appraisal
    expr = eng.expressor.describe(eng.state, top_k=5, min_activation=0.03)
    fired = [
        {"zh": en.zh, "word": en.word, "cat": en.category,
         "intensity": _r(en.intensity, 3), "family": en.family}
        for en in expr.entries
    ]
    return {
        "title": title,
        "ev": {
            "category": ev.category.value,
            "goal_impacts": {k: _r(v, 2) for k, v in ev.goal_impacts.items()},
            "agent": ev.caused_by, "intent": INTENT_ZH[ev.intent], "affects": ev.affects,
            "extras": _extras(ev),
            "dims": (f"novelty {ev.novelty:g} · pleasantness {ev.pleasantness:+g} · "
                     f"预期违背 {ev.expectancy_violation:g} · 概率 {ev.probability:g} · "
                     f"紧迫 {ev.urgency:g}"
                     + (f" · 控制感 {ev.control_hint:g}" if ev.control_hint is not None else "")),
        },
        "ap": {
            "rel": _r(ap.goal_relevance), "cond": _r(ap.conduciveness),
            "urg": _r(ap.urgency), "nov": _r(ap.novelty), "ctl": _r(ap.control),
            "int_std": _r(ap.internal_standard), "ext_std": _r(ap.external_standard),
            "agent": ap.causality_agent, "intent": INTENT_ZH[ap.causality_intent],
            "branches": [b.value for b in ap.occ_branches[:4]],
        },
        "fired": fired,
        "after": {
            "mood": _r(eng.state.mood.valence, 3),
            "residue": _r(eng.state.arousal_residue, 3),
            "rumination": _r(getattr(eng.state, "rumination", 0.0), 3),
            "charges": {k: _r(v, 2) for k, v in eng.state.charges.items()},
        },
        "say": r.expression.summary,
    }


def _fire(agent: AgentProfile, ev: Event, top: int = 3) -> list:
    """变体点燃集合：孤立运行取表达层前 N（带分档词）。"""
    eng = EmotionEngine(agent)
    eng.process(ev, dt_minutes=1.0)
    expr = eng.expressor.describe(eng.state, top_k=top, min_activation=0.03)
    return [{"zh": en.zh, "word": en.word, "cat": en.category,
             "intensity": _r(en.intensity, 2), "family": en.family}
            for en in expr.entries]


def _rep_events() -> dict:
    """11 类代表事件与变体（构造为手写叙事场景；点燃结果全部引擎真算）。
    A–K 中在 demo 八幕出现过的类直接复用八幕事件，保证与回放页同源。"""
    L, T, F, C, A, V, G, N, I, B, K = (EventCategory.LOSS, EventCategory.THREAT,
                                       EventCategory.BOND, EventCategory.FRUSTRATION,
                                       EventCategory.ACHIEVEMENT, EventCategory.VIOLATION,
                                       EventCategory.COMPARISON, EventCategory.NOVELTY,
                                       EventCategory.AESTHETIC, EventCategory.BODY,
                                       EventCategory.FICTION)
    return {
        "A_loss": ("相伴多年的宠物突然离世", Event(
            L, affects="self", caused_by=None, intent=Intent.NONE,
            goal_impacts={"bond": -0.9}, novelty=0.5, pleasantness=-0.8,
            expectancy_violation=0.6, probability=1.0, urgency=0.1, reversibility=0.0), [
            ("久病后离世（早有预期）", Event(
                L, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={"bond": -0.9}, novelty=0.1, pleasantness=-0.7,
                expectancy_violation=0.1, probability=1.0, urgency=0.1, reversibility=0.0)),
            ("失联而非离世（可能找回）", Event(
                L, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={"bond": -0.7}, novelty=0.6, pleasantness=-0.6,
                expectancy_violation=0.5, probability=0.3, urgency=0.3, reversibility=0.6)),
        ]),
        "B_threat": ("家人深夜未归，电话始终不通", Event(
            T, affects="family", caused_by=None, intent=Intent.UNKNOWN,
            goal_impacts={"bond": -0.7}, novelty=0.6, pleasantness=-0.6,
            expectancy_violation=0.5, probability=0.7, urgency=0.8, control_hint=0.1), [
            ("确知凶险正在发生", Event(
                T, affects="family", caused_by=None, intent=Intent.UNKNOWN,
                goal_impacts={"bond": -0.8}, novelty=0.8, pleasantness=-0.8,
                expectancy_violation=0.7, probability=0.95, urgency=0.9, control_hint=0.1)),
            ("远期隐忧（复查通知）", Event(
                T, affects="family", caused_by=None, intent=Intent.UNKNOWN,
                goal_impacts={"bond": -0.5}, novelty=0.4, pleasantness=-0.4,
                expectancy_violation=0.3, probability=0.3, urgency=0.1, control_hint=0.3)),
            ("虚惊一场（平安归来）", Event(
                T, affects="family", caused_by=None, intent=Intent.NONE,
                goal_impacts={"bond": 0.3}, novelty=0.7, pleasantness=0.5,
                expectancy_violation=0.6, probability=1.0, control_hint=0.5,
                prior_threat_resolved=True)),
        ]),
        "C_frustration": ("方案第三次被驳回，窗口又要重排", Event(
            C, affects="self", caused_by="经办人", intent=Intent.UNKNOWN,
            goal_impacts={"esteem": -0.5}, novelty=0.3, pleasantness=-0.5,
            expectancy_violation=0.5, probability=1.0, urgency=0.3, control_hint=0.2), [
            ("换成故意刁难", Event(
                C, affects="self", caused_by="主管", intent=Intent.DELIBERATE,
                goal_impacts={"esteem": -0.6}, novelty=0.4, pleasantness=-0.6,
                expectancy_violation=0.5, probability=1.0, urgency=0.4, control_hint=0.6)),
            ("自己失误导致返工", Event(
                C, affects="self", caused_by="self", intent=Intent.DELIBERATE,
                goal_impacts={"esteem": -0.5}, novelty=0.3, pleasantness=-0.5,
                expectancy_violation=0.4, probability=1.0, urgency=0.2, control_hint=0.5)),
            ("排队到窗口前突然关闭", Event(
                C, affects="self", caused_by=None, intent=Intent.UNKNOWN,
                goal_impacts={"esteem": -0.3}, novelty=0.7, pleasantness=-0.5,
                expectancy_violation=0.8, probability=1.0, urgency=0.5, control_hint=0.2)),
        ]),
        # D/E/F 直接复用 demo 八幕事件（与叙事回放页同源）
        "D_achievement": (STORY[5][0], STORY[5][2], [
            ("轻松躺赢（几乎没费力）", Event(
                A, affects="self", caused_by="self", intent=Intent.DELIBERATE,
                goal_impacts={"esteem": 0.8, "craft": 0.6}, novelty=0.9, pleasantness=0.95,
                expectancy_violation=0.95, probability=0.2, urgency=0.9, effort=0.1,
                justice_restored=0.9, justice_target="villain")),
            ("自己指点的人赢了", Event(
                A, affects="hero", caused_by="self", intent=Intent.DELIBERATE,
                goal_impacts={"esteem": 0.4}, novelty=0.6, pleasantness=0.7,
                expectancy_violation=0.4, probability=0.9, effort=0.5)),
            ("险胜（最后一秒才定）", Event(
                A, affects="self", caused_by="self", intent=Intent.DELIBERATE,
                goal_impacts={"esteem": 0.8, "craft": 0.6}, novelty=0.9, pleasantness=0.95,
                expectancy_violation=0.95, probability=0.15, urgency=0.95, effort=0.9,
                prior_adversity_resolved=True, justice_restored=0.9, justice_target="villain")),
        ]),
        "E_violation": (STORY[0][0], STORY[0][2], [
            ("路人无意踩脏新鞋", Event(
                V, affects="self", caused_by="路人", intent=Intent.ACCIDENTAL,
                goal_impacts={"esteem": -0.2}, novelty=0.4, pleasantness=-0.3,
                expectancy_violation=0.3, probability=1.0, control_hint=0.7)),
            ("目睹陌生人被不公对待", Event(
                V, affects="陌生人", caused_by="执法者", intent=Intent.DELIBERATE,
                goal_impacts={"justice": -0.6}, novelty=0.6, pleasantness=-0.6,
                expectancy_violation=0.5, probability=1.0, control_hint=0.3,
                moral=MoralInfo(severity=0.8, victim="陌生人", violator="执法者"))),
        ]),
        "F_bond": (STORY[7][0], STORY[7][2], [
            ("日久生情式渐近（无骤变）", Event(
                F, affects="self", caused_by="亲近的人", intent=Intent.DELIBERATE,
                goal_impacts={"bond": 0.3}, novelty=0.2, pleasantness=0.5, probability=1.0,
                bond=BondInfo(delta=0.4, sudden=False))),
            ("亲近之人决裂", Event(
                F, affects="self", caused_by="挚友", intent=Intent.DELIBERATE,
                goal_impacts={"bond": -0.7}, novelty=0.7, pleasantness=-0.7,
                expectancy_violation=0.7, probability=1.0, control_hint=0.3,
                bond=BondInfo(delta=0.0, sudden=False, break_up=True))),
            ("暧昧对象表白", Event(
                F, affects="self", caused_by="暧昧对象", intent=Intent.DELIBERATE,
                goal_impacts={"bond": 0.5}, novelty=0.7, pleasantness=0.8, probability=1.0,
                bond=BondInfo(delta=0.5, sudden=True, romantic=True))),
        ]),
        "G_comparison": ("同期入职的同事高升，自己原地踏步", Event(
            G, affects="同事", caused_by=None, intent=Intent.NONE,
            goal_impacts={}, novelty=0.3, pleasantness=-0.2, probability=1.0,
            social=SocialInfo(direction="up", deservedness=0.5, domain="status")), [
            ("对方实至名归", Event(
                G, affects="同事", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.3, pleasantness=-0.1, probability=1.0,
                social=SocialInfo(direction="up", deservedness=0.9, domain="status"))),
            ("关系户靠舞弊上位", Event(
                G, affects="同事", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.4, pleasantness=-0.4, probability=1.0,
                social=SocialInfo(direction="up", deservedness=0.1, domain="status"))),
            ("对方不当得利后翻车", Event(
                G, affects="同事", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.6, pleasantness=0.2, probability=1.0,
                social=SocialInfo(direction="down", deservedness=0.85, domain="status"))),
        ]),
        "H_novelty": ("追更的推理剧大反转，谜底揭晓", Event(
            N, affects="self", caused_by=None, intent=Intent.NONE,
            goal_impacts={}, novelty=0.8, pleasantness=0.2,
            expectancy_violation=0.85, probability=1.0, insight=True), [
            ("被提前剧透", Event(
                N, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.1, pleasantness=0.0,
                expectancy_violation=0.05, probability=1.0)),
            ("伏笔没看懂（信息缺口）", Event(
                N, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.75, pleasantness=0.0,
                expectancy_violation=0.5, probability=1.0)),
            ("注水剧情（信息枯竭）", Event(
                N, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.05, pleasantness=0.0,
                expectancy_violation=0.0, probability=1.0)),
        ]),
        "I_aesthetic": ("山顶守到日出，云海漫过脚下", Event(
            I, affects="self", caused_by=None, intent=Intent.NONE,
            goal_impacts={}, novelty=0.4, pleasantness=0.8, probability=1.0,
            aesthetic=AestheticInfo(vastness=0.8, beauty=0.7)), [
            ("大师现场演奏", Event(
                I, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.3, pleasantness=0.6, probability=1.0,
                aesthetic=AestheticInfo(skill=0.9, beauty=0.5))),
            ("目睹陌生人舍身救人", Event(
                I, affects="self", caused_by="路人", intent=Intent.DELIBERATE,
                goal_impacts={}, novelty=0.5, pleasantness=0.5, probability=1.0,
                moral=MoralInfo(severity=0.9, virtue=True),
                aesthetic=AestheticInfo(virtue=0.9))),
            ("街角偶遇的花", Event(
                I, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.2, pleasantness=0.4, probability=1.0,
                aesthetic=AestheticInfo(beauty=0.4))),
        ]),
        "J_body": ("跑完十公里，浑身通透", Event(
            B, affects="self", caused_by=None, intent=Intent.NONE,
            goal_impacts={}, novelty=0.2, pleasantness=0.7, probability=1.0, effort=0.8), [
            ("重感冒昏沉", Event(
                B, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.2, pleasantness=-0.7, probability=1.0)),
            ("深度按摩", Event(
                B, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.0, pleasantness=0.5, probability=1.0)),
            ("暴食后胀腻", Event(
                B, affects="self", caused_by=None, intent=Intent.NONE,
                goal_impacts={}, novelty=0.1, pleasantness=-0.4, probability=1.0)),
        ]),
        "K_fiction": ("代入主角视角：反派步步紧逼，绝境求生", Event(
            K, affects="hero", caused_by="villain", intent=Intent.DELIBERATE,
            goal_impacts={"bond": -0.5}, novelty=0.6, pleasantness=-0.5,
            expectancy_violation=0.5, probability=0.9, urgency=0.7, control_hint=0.1,
            fictionality=1.0, safety_frame=1.0,
            moral=MoralInfo(severity=0.6, victim="hero", violator="villain")), [
            ("安全框架破损（影院真的着火）", Event(
                K, affects="hero", caused_by="villain", intent=Intent.DELIBERATE,
                goal_impacts={"bond": -0.5}, novelty=0.8, pleasantness=-0.8,
                expectancy_violation=0.7, probability=0.95, urgency=0.9, control_hint=0.0,
                fictionality=0.2, safety_frame=0.0,
                moral=MoralInfo(severity=0.6, victim="hero", violator="villain"))),
            ("反派倒霉名场面", Event(
                K, affects="villain", caused_by="public", intent=Intent.DELIBERATE,
                goal_impacts={"justice": 0.6}, novelty=0.7, pleasantness=0.8,
                expectancy_violation=0.6, probability=1.0,
                social=SocialInfo(direction="down", deservedness=0.9, domain="status"),
                fictionality=1.0, safety_frame=1.0)),
            ("嗑 CP 高甜桥段", Event(
                K, affects="hero", caused_by="恋人", intent=Intent.DELIBERATE,
                goal_impacts={"bond": 0.5}, novelty=0.6, pleasantness=0.8,
                probability=1.0, fictionality=1.0, safety_frame=1.0,
                bond=BondInfo(delta=0.5, sudden=True, romantic=True))),
        ]),
    }


def main() -> int:
    agent = AgentProfile.reader_example()

    # ---- 1) 情绪弧线（8 事件）----
    engine = EmotionEngine(agent)
    events = []
    for title, dt, ev in STORY:
        r = engine.process(ev, dt_minutes=dt)
        entries = [
            {"word": en.word, "zh": en.zh, "intensity": round(en.intensity, 3),
             "category": en.category}
            for en in r.expression.entries if en.intensity > 0.04
        ][:4]
        d = r.expression.dims
        events.append({
            "title": title, "dt": dt,
            "words": entries,
            "dims": {"valence": round(d.valence, 3), "arousal": round(d.arousal, 3),
                     "dominance": round(d.dominance, 3),
                     "unpredictability": round(d.unpredictability, 3)},
            "mood": round(engine.state.mood.valence, 3),
            "memory": round(engine.state.memory.remembered_valence, 3),
            "summary": r.expression.summary,
        })

    # ---- 2) 语域对照（最终状态）----
    registers = {}
    for reg in ("formal", "neutral", "colloquial"):
        out = engine.expressor.describe(engine.state, register=reg)
        registers[reg] = {
            "summary": out.summary,
            "words": [{"word": en.word, "intensity": round(en.intensity, 3)}
                      for en in out.entries],
        }

    # ---- 3) 倒 U 曲线：fear_enjoyment 引擎真实函数（安全框架=1、ss=SS）----
    fear_enjoyment = []
    sf, ss_term = 1.0, 0.6 + 0.4 * SS
    for i in range(0, 101):
        fear = i / 100.0
        fear_enjoyment.append({
            "fear": fear,
            "enjoyment": round(_tent(fear, FEAR_ENJOYMENT_PEAK) * sf * ss_term, 4),
        })

    # ---- 4) 管线解剖：事件1（当众羞辱）五阶段 ----
    from emotion_os.generation.catalog import CATALOG
    dissect = EmotionEngine(agent)
    ev1 = STORY[0][2]
    r = dissect.process(ev1, dt_minutes=1.0)
    appraisal = r.appraisal
    pipeline = {
        "event": {"title": STORY[0][0],
                  "category": ev1.category.value,
                  "goal_impacts": ev1.goal_impacts,
                  "severity": ev1.moral.severity if ev1.moral else None},
        "appraisal": {
            "goal_relevance": round(appraisal.goal_relevance, 3),
            "conduciveness": round(appraisal.conduciveness, 3),
            "urgency": round(appraisal.urgency, 3),
            "novelty": round(appraisal.novelty, 3),
            "control": round(appraisal.control, 3),
        },
        "generation": [
            {"cat": ep.category, "zh": CATALOG[ep.category].zh,
             "intensity": round(ep.intensity, 3)}
            for ep in sorted(r.episodes, key=lambda e: -e.intensity)[:4]
        ],
        "dynamics": {
            "mood_after": round(dissect.state.mood.valence, 3),
            "residue": round(dissect.state.arousal_residue, 3),
            "charges": {k: round(v, 3) for k, v in dissect.state.charges.items()},
        },
        "expression": {
            "neutral": r.expression.summary,
            "entries": [{"word": en.word, "intensity": round(en.intensity, 3)}
                        for en in r.expression.entries[:3]],
            "dims": {"v": round(r.expression.dims.valence, 2),
                     "a": round(r.expression.dims.arousal, 2)},
        },
    }

    # ---- 5) 全量类型空间：事件类型 + 情绪类别全景 ----
    # 事件类型（A–K）：枚举值 + docstring 定义句 + 生活化例子（手写内容示例，非引擎数值）
    _EVENT_EGS = {
        "A_loss": "挚爱的角色在结局死去；钱包丢了",
        "B_threat": "体检报告等待复查；深夜听到异响",
        "C_frustration": "排队的窗口突然关闭；被已读不回",
        "D_achievement": "压哨绝杀；方案被客户点名采用",
        "E_violation": "被插队还被推搡；上司抢走署名",
        "F_bond": "失散亲人重逢；暧昧对象表白",
        "G_comparison": "同事升职；刷到别人的度假照",
        "H_novelty": "剧透前的反转；谜底揭晓的一瞬",
        "I_aesthetic": "山顶看日出；听到副歌起鸡皮疙瘩",
        "J_body": "跑完十公里的通透；重感冒的昏沉",
        "K_fiction": "代入主角视角经历的一切",
    }
    # 事件类型（A–K）完整档案：定义/例子为手写标注；点燃与余波数值全部引擎真算
    rep_events = _rep_events()
    story_acts: dict[str, list[int]] = {}
    for i, (_t, _dt, ev) in enumerate(STORY):
        story_acts.setdefault(ev.category.value, []).append(i + 1)

    event_types = []
    for cat in EventCategory:
        tid = cat.value
        meta = _EVT_META[tid]
        title, rep_ev, variants = rep_events[tid]
        event_types.append({
            "id": tid, "zh": meta["zh"], "def": meta["def"],
            "eg": _EVENT_EGS.get(tid, ""),
            "label": meta["label"], "valence": meta["valence"], "attr": meta["attr"],
            "knob": meta["knob"],
            "rep": _dissect(agent, rep_ev, title),
            "variants": [{"label": vlabel, "fired": _fire(agent, vev)}
                         for vlabel, vev in variants],
            "acts": story_acts.get(tid, []),
            "tests": meta["tests"], "rules": meta["rules"],
        })

    # 情绪类别全量（88 类）：家族分组 + 4D 原型 + 行动倾向 + 半衰期 + 词表覆盖
    from emotion_os.core.state import FAMILY_HALF_LIFE_MIN
    from emotion_os.expression.lexicon import _LADDERS, _REGISTER_LADDERS
    categories = []
    families: dict[str, list] = {}
    for c in CATALOG.values():
        item = {
            "id": c.id, "zh": c.zh, "en": c.en, "family": c.family,
            "v": c.valence, "a": c.arousal, "d": c.dominance, "u": c.unpredictability,
            "tendency": c.tendency,
            "half_life": HALF_LIFE_BY_CATEGORY.get(c.id, FAMILY_HALF_LIFE_MIN.get(c.family)),
            "ladder": [[th, w] for th, w in _LADDERS.get(c.id, [])],
            "reg_ladders": {
                reg: ladder for (cid, reg), ladder in _REGISTER_LADDERS.items() if cid == c.id
            },
        }
        categories.append(item)
        families.setdefault(c.family, []).append(c.zh)

    # ---- 6) 评价维度全表（AppraisalResult 全部字段，SEC 四检查分组）----
    appraisal_dims = [
        ("SEC① 相关性", "novelty", "新异性/突发性", "0–1"),
        ("SEC① 相关性", "pleasantness", "内在愉悦度", "−1–1"),
        ("SEC① 相关性", "goal_relevance", "目标/需要相关性（为零则零情绪）", "0–1"),
        ("SEC② 含义", "conduciveness", "目标促进（+）/阻碍（−）", "−1–1"),
        ("SEC② 含义", "causality_agent", "归因对象（谁干的）", "id / None"),
        ("SEC② 含义", "causality_intent", "归因故意性", "deliberate/accidental/unknown/none"),
        ("SEC② 含义", "outcome_probability", "结果概率", "0–1"),
        ("SEC② 含义", "expectancy_violation", "预期违背", "0–1"),
        ("SEC② 含义", "urgency", "紧迫性", "0–1"),
        ("SEC③ 应对潜力", "control", "能改变它吗", "0–1"),
        ("SEC③ 应对潜力", "power", "能承受它吗", "0–1"),
        ("SEC③ 应对潜力", "adjustment", "能调整适应吗", "0–1"),
        ("SEC④ 规范意义", "internal_standard", "自我理想：违反（−）…符合（+）", "−1–1"),
        ("SEC④ 规范意义", "external_standard", "群体规范：违反（−）…美德（+）", "−1–1"),
        ("派生", "occ_branches", "适用的 OCC 分支（可多个）", "枚举组"),
        ("派生", "primary_branch", "主分支", "枚举"),
        ("派生", "safety_frame", "安全框架（虚构保护罩）", "0–1"),
        ("派生", "fictionality", "虚构度", "0–1"),
        ("派生", "affects", "情绪主体（谁在感受）", "id"),
        ("派生", "n_goals_affected", "受影响目标数", "整数"),
    ]

    # ---- 7) 动力学与强度常数全表（一行一条，含出处注记——出处取自代码注释）----
    from emotion_os import dynamics as dyn
    from emotion_os.generation.intensity import LOSS_AVERSION, RESIDUE_GAIN, STATE_AMP_SLEEP
    dynamics_consts = [
        ("习惯化每步乘数", "HABITUATION_DECAY", dyn.HABITUATION_DECAY, "同刺激重复呈现的激活乘数", "自设（文献为双时间尺度，无单一值）"),
        ("敏感化放大", "SENSITIZATION_GAIN", dyn.SENSITIZATION_GAIN, "创伤相关线索的反应增强", "自设（§4.2 机制方向）"),
        ("唤醒残余半衰期", "RESIDUE_HALF_LIFE", dyn.RESIDUE_HALF_LIFE, "兴奋转移残余窗（分钟）", "Zillmann 1971「3–5 分钟强残余」一致"),
        ("残余摄入比", "RESIDUE_INTAKE", dyn.RESIDUE_INTAKE, "发作唤醒进入残余的比例", "自设"),
        ("心情 EMA 权重", "MOOD_EMA_WEIGHT", dyn.MOOD_EMA_WEIGHT, "单事件对心情层的慢速影响", "量级参照 Kuppens 2010 惯性 0.20–0.33"),
        ("反刍半衰期", "RUMINATION_HALF_LIFE", dyn.RUMINATION_HALF_LIFE, "意难平余韵（分钟，小时级）", "自设（意难平时程）"),
        ("反刍增益", "RUMINATION_GAIN", dyn.RUMINATION_GAIN, "不可逆损失→反刍压力增量", "自设"),
        ("对象记账半衰期", "CHARGE_HALF_LIFE", dyn.CHARGE_HALF_LIFE, "对冒犯者的怒账衰减（分钟）", "自设"),
        ("wanting 池半衰期", "WANTING_HALF_LIFE", dyn.WANTING_HALF_LIFE, "欲望池衰减（分钟，慢于快感）", "自设（Berridge 无文献常数）"),
        ("liking 池半衰期", "LIKING_HALF_LIFE", dyn.LIKING_HALF_LIFE, "快感池衰减（分钟，快衰减）", "自设（同上）"),
        ("恐惧享受顶点", "FEAR_ENJOYMENT_PEAK", FEAR_ENJOYMENT_PEAK, "倒 U 最适恐惧点", "Andersen 2020 OSF 拟合（CI 0.59–1.09）"),
        ("损失厌恶系数 λ", "LOSS_AVERSION", LOSS_AVERSION, "损失侧强度放大（约 2:1）", "T&K 1992=2.25 / Brown 2024≈1.955，代码取 2.0"),
        ("残余加成", "RESIDUE_GAIN", RESIDUE_GAIN, "唤醒残余对高唤醒类别的加成", "自设（兴奋转移幅度）"),
        ("睡眠剥夺放大", "STATE_AMP_SLEEP", STATE_AMP_SLEEP, "睡眠不足时的强度放大", "杏仁核反应 +~60%（§4.2）"),
    ]
    family_halflives = [
        (fam, FAMILY_HALF_LIFE_MIN[fam]) for fam in FAMILY_HALF_LIFE_MIN
    ]

    # ---- 8) 参数扫描矩阵（11 类全覆盖：每类一个事件构造器，引擎真算，前端查表）----
    # 11 类 × 冲击 7 档 × 故意性 3 档 × 控制感 3 档 = 693 组。
    # 修正旧矩阵 4 处语义缺陷：B 扫 safety 目标（reader 画像无此目标→恐惧从不出场）；
    # D 归因"对方"（自豪路径从不触发）；F/G 未带 BondInfo/SocialInfo（联结族与羡慕分流从不出场）。
    def _sim_event(tid: str, imp: float, it: Intent, ctl: float) -> Event:
        neg, pos = min(0.0, imp), max(0.0, imp)
        if tid == "A_loss":
            return Event(EventCategory.LOSS, "失去", affects="self", intent=it,
                         goal_impacts={"bond": imp}, novelty=0.2, pleasantness=neg,
                         probability=0.9, urgency=0.1, control_hint=ctl, reversibility=0.1)
        if tid == "B_threat":
            return Event(EventCategory.THREAT, "遇威胁", affects="family", caused_by="对方",
                         intent=it, goal_impacts={"bond": imp}, novelty=0.5, pleasantness=neg,
                         probability=0.7, urgency=0.8, control_hint=ctl)
        if tid == "C_frustration":
            return Event(EventCategory.FRUSTRATION, "受阻", affects="self", caused_by="经办人",
                         intent=it, goal_impacts={"esteem": imp}, novelty=0.3,
                         pleasantness=neg * 0.8, expectancy_violation=0.4, probability=1.0,
                         urgency=0.3, control_hint=ctl)
        if tid == "D_achievement":
            return Event(EventCategory.ACHIEVEMENT, "有成就", affects="self", caused_by="self",
                         intent=it, goal_impacts={"esteem": imp}, novelty=0.3,
                         pleasantness=pos * 0.6, probability=0.9, effort=0.8, control_hint=ctl)
        if tid == "E_violation":
            kw = dict(category=EventCategory.VIOLATION, description="被冒犯", affects="self",
                      caused_by="对方", intent=it, goal_impacts={"esteem": imp}, novelty=0.4,
                      pleasantness=neg * 0.8, expectancy_violation=0.3, probability=0.9,
                      urgency=0.4, control_hint=ctl)
            if imp < 0:
                kw["moral"] = MoralInfo(severity=-neg, victim="self", violator="对方")
            return Event(**kw)
        if tid == "F_bond":
            b = None
            if imp > 0.05:
                b = BondInfo(delta=imp, sudden=True)
            elif imp < -0.05:
                b = BondInfo(delta=0.0, sudden=False, break_up=True)
            return Event(EventCategory.BOND, "关系变动", affects="self", caused_by="亲近的人",
                         intent=it, goal_impacts={"bond": imp}, novelty=0.5,
                         pleasantness=imp * 0.7, probability=0.9, control_hint=ctl, bond=b)
        if tid == "G_comparison":
            return Event(EventCategory.COMPARISON, "与人比较", affects="同事", intent=it,
                         goal_impacts={}, novelty=0.3, pleasantness=imp * 0.3, probability=0.9,
                         control_hint=ctl,
                         social=SocialInfo(direction="up" if imp <= 0 else "down",
                                           deservedness=0.5, domain="status"))
        if tid == "H_novelty":
            return Event(EventCategory.NOVELTY, "遇新奇", affects="self", intent=it,
                         goal_impacts={}, novelty=pos if imp > 0 else 0.05,
                         expectancy_violation=pos * 0.8, probability=0.9, control_hint=ctl,
                         insight=imp > 0.6)
        if tid == "I_aesthetic":
            aes = AestheticInfo(vastness=pos, beauty=pos) if imp > 0 else None
            return Event(EventCategory.AESTHETIC, "审美体验", affects="self", intent=it,
                         goal_impacts={}, novelty=0.3, pleasantness=imp * 0.6, probability=0.9,
                         control_hint=ctl, aesthetic=aes)
        if tid == "J_body":
            return Event(EventCategory.BODY, "身体状态", affects="self", intent=it,
                         goal_impacts={}, novelty=0.15, pleasantness=imp, probability=0.9,
                         control_hint=ctl)
        # K_fiction：虚构框架内的剧情冲击（牵挂 hero，施加者 villain）
        kw = dict(category=EventCategory.FICTION, description="虚构剧情", affects="hero",
                  caused_by="villain", intent=it, goal_impacts={"bond": imp}, novelty=0.6,
                  pleasantness=neg * 0.6, expectancy_violation=0.4, probability=0.9,
                  urgency=0.6, control_hint=ctl, fictionality=1.0, safety_frame=1.0)
        if imp < 0:
            kw["moral"] = MoralInfo(severity=-neg * 0.8, victim="hero", violator="villain")
        return Event(**kw)

    SIM_ORDER = ["A_loss", "B_threat", "C_frustration", "D_achievement", "E_violation",
                 "F_bond", "G_comparison", "H_novelty", "I_aesthetic", "J_body", "K_fiction"]
    IMPACTS = [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0, 0.0]
    INTENTS = [Intent.DELIBERATE, Intent.ACCIDENTAL, Intent.UNKNOWN]
    CONTROLS = [0.2, 0.5, 0.8]
    sim_matrix = {}
    for tid in SIM_ORDER:
        meta = _EVT_META[tid]
        rows = []
        for imp in IMPACTS:
            for it in INTENTS:
                for ctl in CONTROLS:
                    e = EmotionEngine(agent)
                    r = e.process(_sim_event(tid, imp, it, ctl), dt_minutes=1.0)
                    top = [
                        {"zh": CATALOG[ep.category].zh, "intensity": round(ep.intensity, 2),
                         "cat": ep.category}
                        for ep in sorted(r.episodes, key=lambda x: -x.intensity)[:5]
                        if ep.intensity > 0.05
                    ]
                    d = r.expression.dims
                    rows.append({
                        "imp": imp, "intent": it.value, "ctl": ctl,
                        "top": top, "v": round(d.valence, 2), "a": round(d.arousal, 2),
                        "say": r.expression.summary,
                    })
        sim_matrix[tid] = {"label": meta["label"], "knob": meta["knob"], "rows": rows}

    # ---- 9) 峰终变体（BE/中性/HE 三结局）----
    endings = []
    for tag, pleasant, reversibility, note in [
        ("BE 惨烈", -0.9, 0.0, "挚爱角色牺牲，无可挽回"),
        ("中性留白", 0.0, 0.5, "开放式结局"),
        ("HE 圆满", 0.8, 1.0, "失散亲人重逢相拥"),
    ]:
        eng2 = EmotionEngine(AgentProfile.reader_example())
        for title, dt, ev in STORY[:-1]:
            eng2.process(ev, dt_minutes=dt)
        end_ev = STORY[-1][2]
        from dataclasses import replace as _dc_replace
        end_ev = _dc_replace(end_ev, pleasantness=pleasant, reversibility=reversibility,
                             goal_impacts={"bond": pleasant}, description=note)
        r2 = eng2.process(end_ev, dt_minutes=180.0)
        endings.append({
            "tag": tag, "note": note,
            "memory": round(eng2.state.memory.remembered_valence, 2),
            "peak": round(eng2.state.memory.peak_valence, 2),
            "end_v": round(eng2.state.memory.end_valence, 2),
            "say": r2.expression.summary,
        })

    # ---- 10) 机制图鉴卡片（内容性数据，出处为真）----
    mechs = [
        {"t": "恐惧享受倒 U", "tag": "生成", "one": "安全框架内，享受随恐惧先升后降，峰值在「不能忍受的下一档」",
         "pts": ["身体发出负信号 + 认知确认安全 = 享受", "顶点 0.84 由 Andersen 2020 鬼屋研究 OSF 开放数据拟合",
                 "安全框架破损失（真危险）→ 享受归零、纯恐惧"],
         "src": "Rozin et al. 2013；Andersen et al. 2020（OSF 复现）"},
        {"t": "峰终定律", "tag": "动力学", "one": "记忆评分 ≈ 峰值×0.5 + 结尾×0.5，过程时长不计",
         "pts": ["BE/烂尾的意难平由「高峰+负终值」结构解释", "时长加权会稀释终值 → 意难平不可复现",
                 "等权为模型惯例，精确相对权重文献未报告"],
         "src": "Kahneman et al. 1993；Redelmeier et al. 2003"},
        {"t": "兴奋转移", "tag": "动力学", "one": "未消退的唤醒残余转移到后续情绪并放大强度",
         "pts": ["绝杀 = fiero × 兴奋转移：先悬念后胜利的情绪强于直接胜利",
                 "残余窗半衰期 10 分钟：久远的前置事件不再放大", "争吵后立刻收到好消息，喜悦被残余唤醒放大"],
         "src": "Zillmann 1971；v0.3 时序修复后残余窗真正生效"},
        {"t": "wanting ≠ liking", "tag": "动力学", "one": "「想要」与「喜欢」是两个独立系统",
         "pts": ["解释刷短视频停不下来却并不快乐", "引擎分两个池：wanting 慢衰减（30min）、liking 快衰减（12min）",
                 "「上头」= wanting 池显著超过 liking 池"],
         "src": "Berridge；双池半衰期为自设（无文献常数）"},
        {"t": "损失厌恶", "tag": "生成", "one": "同幅度损失的情绪强度 > 同幅度收益，约 2:1",
         "pts": ["丢 100 元的痛 ≈ 得 200 元的快乐", "BE 结局损失侧被 λ=2.0 放大",
                 "λ 实证区间 1.3–2.25，代码取 2.0（从 Brown 2024）"],
         "src": "Tversky & Kahneman 1992；Walasek 2024；Brown 2024"},
        {"t": "kama muta 骤增触发", "tag": "评价", "one": "共享关系突然增强引发「被感动」",
         "pts": ["失散重逢、告白被接受 → 鼻头一酸/泪目", "渐进增强只产生温情，不触发感动",
                 "半衰期 1.5 分钟——感动是爆发式的"],
         "src": "Zickfeld et al. 2018（19 国证据）"},
    ]

    # ---- 11) LLM 端到端（流程 + 真实日志摘录）----
    llm_flow = [
        {"step": "叙事文本", "eg": "「主管当众抢走了小林的方案署名…」"},
        {"step": "CLI 抽取（claude/codex）", "eg": "结构化 JSON：category / goal_impacts / moral…"},
        {"step": "适配器校验+归一", "eg": "范围截断、实体规范化、goal id 契约化"},
        {"step": "引擎全管线", "eg": "评价 → 生成 → 动力学 → 表达"},
        {"step": "中文输出", "eg": "「义愤填膺与满腹委屈交织」"},
    ]
    llm_log = ""
    log_path = ROOT / ".tasks" / "llm-e2e-log.md"
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8")
        # 取最新一节 claude 段的事件1输出（真实摘录）
        seg = text.rfind("## claude CLI")
        if seg > 0:
            chunk = text[seg:seg + 2200]
            for line in chunk.splitlines():
                if line.startswith("- 引擎输出：") or line.startswith("- 中文表达："):
                    llm_log += line + "\n"
                if len(llm_log) > 300:
                    break

    data = {
        "meta": {
            "version": "0.7.0", "categories": len(CATALOG), "tests": 163, "releases": 7,
            "peak": FEAR_ENJOYMENT_PEAK,
            "peak_ci": "[0.59, 1.09]",
        },
        "event_types": event_types,
        "categories": categories,
        "families": {k: len(v) for k, v in families.items()},
        "appraisal_dims": [
            {"group": g, "field": f, "zh": z, "range": r} for g, f, z, r in appraisal_dims
        ],
        "dynamics_consts": [
            {"zh": z, "field": f, "value": v, "meaning": m, "src": s}
            for z, f, v, m, s in dynamics_consts
        ],
        "family_halflives": family_halflives,
        "events": events,
        "registers": registers,
        "fear_enjoyment": fear_enjoyment,
        "pipeline": pipeline,
        "sim_matrix": sim_matrix,
        "endings": endings,
        "mechs": mechs,
        "llm_flow": llm_flow,
        "llm_log": llm_log.strip(),
    }

    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"written: {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")

    # Artifact 片段版：去 html/head/body 外壳（发布骨架会包），从 <title> 到 </script>
    t0 = html.index("<title>")
    t1 = html.index("</script>") + len("</script>")
    frag = html[t0:t1]
    frag_path = ROOT / ".tasks" / "visualization-fragment.html"
    frag_path.write_text(frag, encoding="utf-8")
    print(f"fragment: {frag_path}  ({frag_path.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

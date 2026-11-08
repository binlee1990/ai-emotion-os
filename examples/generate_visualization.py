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
    from emotion_os.generation.catalog import CATALOG, HALF_LIFE_BY_CATEGORY
    from emotion_os.generation.mapping import FEAR_ENJOYMENT_PEAK, _tent
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from emotion_os import AgentProfile, EmotionEngine, Event, EventCategory, Intent
    from emotion_os.generation.catalog import CATALOG, HALF_LIFE_BY_CATEGORY
    from emotion_os.generation.mapping import FEAR_ENJOYMENT_PEAK, _tent

sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_story import STORY  # 同一弧线，数据一致

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "visualization.html"
TEMPLATE = Path(__file__).resolve().parent / "visual_template.html"

SS = 0.6  # 与 demo/场景测试一致的中档感觉寻求


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
    event_types = []
    for cat in EventCategory:
        doc = (cat.__doc__ or "").strip()
        event_types.append({
            "id": cat.value, "zh": doc.split("：", 1)[0], "def": doc,
            "eg": _EVENT_EGS.get(cat.value, ""),
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
            "ladder": len(_LADDERS.get(c.id, [])),
            "registers": sorted({reg for (cid, reg) in _REGISTER_LADDERS if cid == c.id}),
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

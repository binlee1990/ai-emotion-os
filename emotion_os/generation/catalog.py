"""情绪类别目录：类别 × 维度双表示的类别侧单一来源（架构合同 §4.2）。

每条：id / 中文 / 英文 / 家族 / 4D 原型（效价-1–1, 唤醒0–1, 支配-1–1, 意外性0–1）/
行动倾向 / wanting-liking 双通道标记（调研 §6.3.6）。
家族来源=调研 §3.3 十二族 + 中文特有词；原型为理论锚定的 v0.1 常数（待标定，见调研附录）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: str
    zh: str
    en: str
    family: str
    valence: float
    arousal: float
    dominance: float
    unpredictability: float
    tendency: str = ""
    wanting: float = 0.0
    liking: float = 0.0


def _c(
    id: str, zh: str, en: str, family: str,
    v: float, a: float, d: float, u: float,
    tendency: str = "", wanting: float = 0.0, liking: float = 0.0,
) -> Category:
    return Category(id, zh, en, family, v, a, d, u, tendency, wanting, liking)


# ---- 家族（调研 §3.3）----
ANGER = "anger"; FEAR = "fear"; DISGUST = "disgust"; SADNESS = "sadness"
JOY = "joy"; SELF_CONSCIOUS = "self_conscious"; SOCIAL_MORAL = "social_moral"
LOVE = "love"; EPISTEMIC = "epistemic"; AESTHETIC = "aesthetic"; PROSPECT = "prospect"

_CATALOG: list[Category] = [
    # 愤怒族（§3.3：阻碍+违范+故意归因+高控制）
    _c("irritation", "恼怒", "irritation", ANGER, -0.3, 0.4, 0.2, 0.1, "言语攻击"),
    _c("frustration", "挫败", "frustration", ANGER, -0.4, 0.55, 0.0, 0.15, "坚持/换路"),
    _c("anger", "愤怒", "anger", ANGER, -0.6, 0.7, 0.4, 0.1, "攻击"),
    _c("indignation", "义愤", "indignation", ANGER, -0.5, 0.65, 0.5, 0.05, "惩罚违规", wanting=0.4),
    _c("rage", "暴怒", "rage", ANGER, -0.8, 0.95, 0.6, 0.2, "失控行攻击"),
    _c("resentment", "怨恨", "resentment", ANGER, -0.4, 0.3, -0.2, 0.0, "记仇"),
    _c("wei_yuan", "委屈", "wei_yuan (unjust treated, no outlet)", ANGER, -0.5, 0.35, -0.5, 0.0, "申辩"),
    _c("bie_qu", "憋屈", "suppressed frustration", ANGER, -0.55, 0.45, -0.6, 0.0, "压抑"),
    # 恐惧族
    _c("anxiety", "焦虑", "anxiety", FEAR, -0.45, 0.55, -0.4, 0.5, "扫描/回避"),
    _c("fear", "恐惧", "fear", FEAR, -0.7, 0.8, -0.5, 0.3, "逃跑"),
    _c("startle", "惊吓", "startle", FEAR, -0.5, 0.9, -0.3, 0.9, "惊跳"),
    _c("horror", "惊骇", "horror", FEAR, -0.85, 0.9, -0.7, 0.4, "僵住/逃离"),
    _c("panic", "恐慌", "panic", FEAR, -0.8, 0.95, -0.8, 0.6, "慌乱"),
    _c("dread", "畏惧", "dread", FEAR, -0.5, 0.35, -0.5, 0.2, "回避"),
    _c("suspense", "悬念", "suspense (hope+fear)", FEAR, -0.2, 0.6, -0.2, 0.7, "注意锁定", wanting=0.5),
    # 厌恶族
    _c("disgust", "厌恶", "disgust", DISGUST, -0.6, 0.4, 0.3, 0.1, "排斥"),
    _c("contempt", "蔑视", "contempt", DISGUST, -0.4, 0.35, 0.6, 0.0, "俯视/疏远"),
    _c("moral_disgust", "道德厌恶", "moral disgust", DISGUST, -0.7, 0.55, 0.4, 0.1, "谴责/远离"),
    # 悲伤族
    _c("sadness", "悲伤", "sadness", SADNESS, -0.6, 0.3, -0.4, 0.0, "退缩"),
    _c("grief", "哀恸", "grief", SADNESS, -0.85, 0.5, -0.7, 0.0, "哀悼"),
    _c("despair", "绝望", "despair", SADNESS, -0.9, 0.25, -0.8, 0.0, "放弃"),
    _c("disappointment", "失望", "disappointment", SADNESS, -0.5, 0.25, -0.3, 0.1, "撤资"),
    _c("heartbreak", "心碎", "heartbreak", SADNESS, -0.8, 0.5, -0.6, 0.1, "哀悼+抗议"),
    _c("loneliness", "孤独", "loneliness", SADNESS, -0.5, 0.2, -0.4, 0.0, "求联结"),
    _c("social_pain", "社会疼痛", "social pain", SADNESS, -0.7, 0.5, -0.6, 0.1, "求重新接纳"),
    _c("empathic_pain", "共情疼痛", "empathic pain", SADNESS, -0.6, 0.45, -0.3, 0.05, "关注对方"),
    _c("xin_teng", "心疼", "aching tenderness", SADNESS, -0.5, 0.4, -0.2, 0.05, "照料"),
    _c("yi_nan_ping", "意难平", "unresolved regret rumination", SADNESS, -0.55, 0.35, -0.3, 0.05, "反刍"),
    # 快乐族（含 fiero/爽/解气 等成就-正义复合）
    _c("pleasure", "愉快", "pleasure", JOY, 0.5, 0.35, 0.2, 0.0, "", liking=0.8),
    _c("joy", "喜悦", "joy", JOY, 0.7, 0.6, 0.3, 0.05, "", liking=0.9),
    _c("contentment", "满足", "contentment", JOY, 0.5, 0.2, 0.2, 0.0, "", liking=0.8),
    _c("excitement", "兴奋", "excitement", JOY, 0.6, 0.8, 0.3, 0.2, "", wanting=0.5),
    _c("ecstasy", "狂喜", "ecstasy", JOY, 0.9, 0.9, 0.5, 0.3, "", wanting=0.7, liking=0.9),
    _c("serenity", "安宁", "serenity", JOY, 0.4, 0.1, 0.1, 0.0, "", liking=0.8),
    _c("fiero", "胜利感", "fiero", JOY, 0.8, 0.85, 0.7, 0.15, "庆祝/再战", liking=0.7),
    _c("amusement", "愉悦(被逗乐)", "amusement", JOY, 0.55, 0.6, 0.3, 0.3, "笑", liking=0.8),
    _c("jie_qi", "解气", "justice satisfaction", JOY, 0.65, 0.7, 0.6, 0.05, "畅快", liking=0.7),
    _c("shuang", "爽", "cathartic release", JOY, 0.8, 0.8, 0.7, 0.1, "宣泄", liking=0.8),
    _c("schadenfreude", "幸灾乐祸", "schadenfreude", JOY, 0.5, 0.55, 0.5, 0.1, "旁观", liking=0.5),
    _c("happy_for", "为他高兴", "happy-for", JOY, 0.55, 0.5, 0.2, 0.05, "祝贺"),
    _c("gloating", "得意", "gloating", JOY, 0.6, 0.6, 0.6, 0.05, "炫耀"),
    # 自我意识族
    _c("shame", "羞耻", "shame", SELF_CONSCIOUS, -0.6, 0.45, -0.7, 0.0, "躲藏"),
    _c("guilt", "内疚", "guilt", SELF_CONSCIOUS, -0.5, 0.4, -0.4, 0.0, "修复"),
    _c("embarrassment", "尴尬", "embarrassment", SELF_CONSCIOUS, -0.4, 0.55, -0.4, 0.3, "掩饰/笑化解"),
    _c("vicarious_embarrassment", "替代性尴尬", "vicarious embarrassment", SELF_CONSCIOUS, -0.35, 0.5, -0.2, 0.3, "捂脸/移开视线"),
    _c("pride", "自豪", "pride (authentic)", SELF_CONSCIOUS, 0.7, 0.55, 0.7, 0.05, "分享/再接再厉"),
    _c("po_fang", "破防", "defense breakthrough", SELF_CONSCIOUS, -0.3, 0.9, -0.5, 0.5, "情绪决堤"),
    # 社会-道德族
    _c("gratitude", "感激", "gratitude", SOCIAL_MORAL, 0.7, 0.45, 0.0, 0.0, "回报/联结"),
    _c("elevation", "崇高", "elevation", SOCIAL_MORAL, 0.65, 0.4, 0.1, 0.05, "效仿"),
    _c("admiration", "钦佩", "admiration", SOCIAL_MORAL, 0.6, 0.45, 0.1, 0.05, "学习"),
    _c("sympathy", "同情", "sympathy", SOCIAL_MORAL, -0.35, 0.3, 0.2, 0.0, "帮助"),
    _c("compassion", "慈悲", "compassion", SOCIAL_MORAL, -0.2, 0.35, 0.3, 0.0, "救助"),
    _c("benign_envy", "良性羡慕", "benign envy", SOCIAL_MORAL, -0.2, 0.5, -0.1, 0.1, "向上努力"),
    _c("malicious_envy", "恶意羡慕", "malicious envy", SOCIAL_MORAL, -0.6, 0.55, -0.4, 0.1, "贬损对方"),
    _c("jealousy", "嫉妒", "jealousy", SOCIAL_MORAL, -0.65, 0.6, -0.4, 0.2, "守护关系/攻击第三者"),
    _c("betrayal", "背叛感", "betrayal", SOCIAL_MORAL, -0.75, 0.55, -0.5, 0.3, "抗议/断联"),
    # 爱-依恋族
    _c("romantic_passion", "浪漫激情", "romantic passion", LOVE, 0.75, 0.65, 0.1, 0.1, "追求", wanting=0.9, liking=0.7),
    _c("heart_flutter", "心动", "heart flutter", LOVE, 0.65, 0.7, 0.0, 0.25, "靠近", wanting=0.6),
    _c("tenderness", "柔情", "tenderness", LOVE, 0.6, 0.3, 0.2, 0.0, "照料", liking=0.8),
    _c("attachment_warmth", "依恋温暖", "attachment warmth", LOVE, 0.55, 0.25, 0.15, 0.0, "依偎", liking=0.8),
    _c("kama_muta", "被感动", "kama muta / being moved", LOVE, 0.7, 0.75, 0.0, 0.4, "奉献/分享", liking=0.9),
    _c("ke_dao", "磕到了", "vicarious relation joy", LOVE, 0.65, 0.6, 0.1, 0.2, "分享", liking=0.8),
    # 认识性族
    _c("curiosity", "好奇", "curiosity", EPISTEMIC, 0.3, 0.5, 0.2, 0.4, "探索", wanting=0.6),
    _c("interest", "兴趣", "interest", EPISTEMIC, 0.4, 0.4, 0.2, 0.2, "投入", wanting=0.4),
    _c("surprise", "惊讶", "surprise", EPISTEMIC, 0.1, 0.7, 0.0, 0.95, "定向"),
    _c("shock", "震惊", "shock", EPISTEMIC, -0.3, 0.85, -0.3, 0.95, "停顿"),
    _c("confusion", "困惑", "confusion", EPISTEMIC, -0.25, 0.45, -0.2, 0.5, "搜寻"),
    _c("aha", "顿悟", "insight/aha", EPISTEMIC, 0.7, 0.6, 0.4, 0.3, "整合", liking=0.7),
    _c("boredom", "无聊", "boredom", EPISTEMIC, -0.3, 0.15, 0.0, 0.0, "脱离/找刺激", wanting=0.3),
    _c("numb", "麻了", "numbing (overload shutdown)", EPISTEMIC, -0.2, 0.05, -0.3, 0.0, "断连/钝化"),
    _c("fascination", "着迷", "fascination", EPISTEMIC, 0.5, 0.5, 0.1, 0.2, "沉浸", wanting=0.7, liking=0.7),
    # 审美族
    _c("beauty", "美感", "feeling of beauty", AESTHETIC, 0.6, 0.35, 0.1, 0.05, "品味", liking=0.9),
    _c("awe", "敬畏", "awe", AESTHETIC, 0.45, 0.6, -0.3, 0.3, "顺应/小我化", liking=0.8),
    _c("nostalgia", "怀旧", "nostalgia", AESTHETIC, 0.35, 0.3, 0.0, 0.0, "回味", liking=0.7),
    _c("relaxation", "放松", "relaxation", AESTHETIC, 0.45, 0.1, 0.2, 0.0, "松弛", liking=0.8),
    _c("vitality", "活力", "vitality", AESTHETIC, 0.6, 0.65, 0.4, 0.1, "行动", wanting=0.5, liking=0.6),
    # 前景-成就族
    _c("hope", "希望", "hope", PROSPECT, 0.4, 0.5, 0.1, 0.35, "准备", wanting=0.5),
    _c("anticipation", "期待", "anticipation", PROSPECT, 0.55, 0.55, 0.2, 0.2, "等待", wanting=0.6),
    _c("relief", "解脱", "relief", PROSPECT, 0.65, 0.35, 0.3, 0.05, "松弛", liking=0.7),
    _c("regret", "后悔", "regret", PROSPECT, -0.5, 0.3, -0.4, 0.05, "反事实修正"),
    _c("accomplishment", "成就感", "accomplishment", PROSPECT, 0.7, 0.5, 0.6, 0.05, "巩固", liking=0.7),
    _c("fear_enjoyment", "怕并快乐着", "feared enjoyed (benign masochism)", PROSPECT, 0.55, 0.75, 0.2, 0.4, "再来一次", wanting=0.6, liking=0.7),
    # v0.2 补全（复审 P2 + 调研 §5.3/§5.5/§6.2）
    _c("comfort", "安慰", "downward-comparison comfort", JOY, 0.35, 0.25, 0.1, 0.0, "自我宽慰", liking=0.5),
    _c("superiority", "优越感", "superiority", SOCIAL_MORAL, 0.3, 0.35, 0.55, 0.05, "自我抬升"),
    _c("shang_tou", "上头", "absorbed craving (wanting-dominant)", EPISTEMIC, 0.35, 0.75, 0.1, 0.2, "停不下来", wanting=0.9, liking=0.2),
    _c("naches", "欣慰(纳赫)", "naches (pride in protege's success)", SOCIAL_MORAL, 0.65, 0.4, 0.3, 0.05, "为后辈骄傲"),
    _c("chills", "颤栗快感", "chills (peak hedonic response)", AESTHETIC, 0.75, 0.85, 0.0, 0.3, "", liking=0.9),
    _c("collective_effervescence", "集体欢腾", "collective effervescence", SOCIAL_MORAL, 0.7, 0.7, 0.3, 0.1, "融入集体", liking=0.7),
    # v0.8 补全（深度调研缺口：文献有独立地位、引擎此前折入或未建——§8 v0.8 候选清单）
    # 被排斥（Williams 需求威胁模型）：被无视感是排斥定性访谈核心主题
    _c("invisibility", "被无视感", "invisibility (ostracism-induced)", SADNESS, -0.55, 0.35, -0.5, 0.1, "求被看见/重新加入"),
    # PLAY 嬉戏（Panksepp 七原生系统之一）：rough-and-tumble 社交欢乐
    _c("play_joy", "玩闹欢腾", "playful social joy (Panksepp PLAY)", JOY, 0.7, 0.85, 0.3, 0.2, "追逐打闹/笑作一团", wanting=0.5, liking=0.9),
    # LUST 欲望域（Panksepp）：wanting 主导的对象特异渴望（动机结构，不建显式性内容）
    _c("craving", "渴望", "longing/desire (LUST-system craving)", LOVE, 0.15, 0.7, -0.2, 0.1, "靠近/求接触", wanting=0.95, liking=0.3),
    # 目标冲突/混合情绪：正负并存的认识性紧张
    _c("ambivalence", "矛盾", "ambivalence (co-activated mixed valence)", EPISTEMIC, 0.0, 0.5, -0.3, 0.2, "悬而未决/摇摆"),
    # 近失效应（Clark 2009/2010）：差一点激活与真赢相似并驱动再试——wanting 高是本类要点
    _c("bu_gan_xin", "不甘心", "near-miss vexation (so close)", PROSPECT, -0.45, 0.65, -0.1, 0.5, "再试一次", wanting=0.85, liking=0.1),
]

CATALOG: dict[str, Category] = {c.id: c for c in _CATALOG}
FAMILY_OF: dict[str, str] = {c.id: c.family for c in _CATALOG}

# 类别级半衰期覆盖（分钟）；其余按家族默认（core.state.FAMILY_HALF_LIFE_MIN）。待标定。
HALF_LIFE_BY_CATEGORY: dict[str, float] = {
    "kama_muta": 1.5,     # 被感动 1–2 分钟内（调研 §1.5.8）
    "grief": 240.0,
    "jie_qi": 20.0,
    "shuang": 25.0,
    "po_fang": 30.0,
    "ambivalence": 30.0,  # 决策性撕扯比认识性惊异持久（epistemic 族默认 5 分钟过短；自设待标定）
}

assert len(CATALOG) >= 50, "架构合同：类别目录 ≥50"
for _need in ("wei_yuan", "jie_qi", "shuang", "bie_qu", "xin_teng", "yi_nan_ping", "po_fang", "ke_dao", "numb"):
    assert _need in CATALOG, f"中文特有词缺失: {_need}"

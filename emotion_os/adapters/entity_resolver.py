# -*- coding: utf-8 -*-
"""跨事件实体规范化（v0.4）：适配器层的实体消解，引擎 charges 匹配语义不变。

v0.3 LLM 端到端实测缺口：同一实体两次抽取输出不同写法（事件1 violator="主管"、
事件2 justice_target="supervisor"）→ charges 字面匹配不命中 → 解气不触发。
结构化事件输入（显式一致 id）不受影响。

两层防线（均零依赖）：
1. **prompt 注入**（主防线）：`NLEventAdapter.adapt` 把已见实体名单注入抽取
   prompt，要求 LLM 对同指实体复用已见写法——LLM 侧消解最准（它看得懂
   「supervisor 就是那个主管」）。
2. **parse 后归一**（兜底）：LLM 未复用写法时，按别名表（用户注入，如
   {"supervisor": "主管"}）与已见实体（大小写/空白不敏感精确匹配）归一
   Event 的实体字段。不做模糊匹配（编辑距离/音译猜测会误合并不同实体——
   宁可漏归一也不错归一，错归一会让惩罚落到无辜对象上）。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ..core.event import Event

# 值域保留字：不登记、不归一
_RESERVED = {"self", "none", "null", ""}
# affects 的命名空间前缀：归一只作用于实体部分
_PREFIXES = ("group:", "fictional:")


def _split_prefix(name: str) -> tuple[str, str]:
    for p in _PREFIXES:
        if name.startswith(p):
            return p, name[len(p):]
    return "", name


@dataclass
class EntityResolver:
    """已见实体登记 + 别名归一。线程不安全（每会话/适配器一个实例）。

    取舍：stimulus_key 不归一（同为跨事件字面匹配键，但 LLM 实际几乎不输出、
    归一又会污染实体名单）——LLM 写法漂移时习惯化计数静默失效是已知边界。
    goal_impacts 的 goal id 不归一（与 profile 固定词表期内匹配，非跨 LLM 输出匹配）。
    """

    # 表面写法 → 规范名；用户按领域注入，如 {"supervisor": "主管", "boss": "主管"}。
    # 键在构造时归一为 casefold+去空格（注入 "Super Visor" 这类键同样可命中）。
    aliases: dict[str, str] = field(default_factory=dict)
    # 已见规范实体（保留首次写法），登记顺序即 roster 顺序
    seen: list[str] = field(default_factory=list)
    # 归一发生时记入（供调试/断言），不参与逻辑
    renames: list[tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.aliases = {
            k.strip().casefold().replace(" ", ""): v for k, v in self.aliases.items()
        }

    @staticmethod
    def _key(body: str) -> str:
        return body.casefold().replace(" ", "")

    def normalize(self, name: str | None) -> str | None:
        """归一单个实体名：None 透传；保留字归一到小写（引擎字面比较 "self"）；前缀保留只归一主体。"""
        if name is None:
            return None
        raw = name.strip()
        if raw.casefold() in _RESERVED:
            return raw.casefold()
        prefix, body = _split_prefix(raw)
        key = self._key(body)
        if not key:
            return raw
        if key in self.aliases:                       # 1) 别名表（用户领域知识）
            canonical = self.aliases[key]
            if canonical not in self.seen and not any(
                self._key(s) == self._key(canonical) for s in self.seen
            ):
                self.seen.append(canonical)           # 别名先命中时也登记规范名（roster 完整）
        elif any(self._key(s) == key for s in self.seen):  # 2) 已见（大小写/空白不敏感）
            canonical = next(s for s in self.seen if self._key(s) == key)
        else:                                         # 3) 新实体：登记首次写法
            canonical = body
            self.seen.append(canonical)
            return prefix + canonical
        if canonical != body:
            self.renames.append((prefix + body, prefix + canonical))
        return prefix + canonical

    def roster_hint(self) -> str:
        """注入抽取 prompt 的实体名单（空名单返回空串）。"""
        if not self.seen:
            return ""
        names = "、".join(self.seen)
        return f"叙事中的实体若与下列已见实体同指，必须复用同一写法：{names}"

    def resolve_event(self, event: Event) -> Event:
        """归一 Event 的实体字段（caused_by/affects/justice_target/moral.victim/violator）。"""
        updates: dict[str, Any] = {}
        for f in ("caused_by", "affects", "justice_target"):
            val = getattr(event, f)
            if val is not None:
                updates[f] = self.normalize(val)
        if event.moral is not None:
            updates["moral"] = replace(
                event.moral,
                victim=self.normalize(event.moral.victim) or event.moral.victim,
                violator=self.normalize(event.moral.violator),
            )
        return replace(event, **updates) if updates else event

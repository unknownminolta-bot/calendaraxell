from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CategoryRule:
    name: str
    color_id: str
    include_keywords: List[str]
    exclude_keywords: List[str]


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def event_text(event: Dict) -> str:
    parts = [
        event.get("summary", ""),
        event.get("description", ""),
        event.get("location", ""),
    ]
    return normalize(" ".join(parts))


def matches_rule(rule: CategoryRule, text: str) -> bool:
    if not text:
        return False
    include = any(normalize(keyword) in text for keyword in rule.include_keywords)
    if not include:
        return False
    excluded = any(normalize(keyword) in text for keyword in rule.exclude_keywords)
    return not excluded


def classify_event(
    event: Dict,
    rules_by_name: Dict[str, CategoryRule],
    priority: List[str],
) -> Optional[CategoryRule]:
    text = event_text(event)
    for category_name in priority:
        rule = rules_by_name.get(category_name)
        if not rule:
            continue
        if matches_rule(rule, text):
            return rule
    return None


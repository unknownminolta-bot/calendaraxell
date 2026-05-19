from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CategoryRule:
    name: str
    color_id: str
    include_keywords: List[str]
    exclude_keywords: List[str]
    all_day_only: bool = False


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def event_text(event: Dict) -> str:
    parts = [
        event.get("summary", ""),
        event.get("description", ""),
        event.get("location", ""),
    ]
    return normalize(" ".join(parts))


def keyword_matches(keyword: str, text: str) -> bool:
    normalized_keyword = normalize(keyword)
    if not normalized_keyword:
        return False
    # Match whole words/phrases only to avoid false positives like
    # matching "sökt" inside "besökt".
    pattern = rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)"
    return re.search(pattern, text) is not None


def matches_rule(rule: CategoryRule, text: str) -> bool:
    if not text:
        return False
    include = any(keyword_matches(keyword, text) for keyword in rule.include_keywords)
    if not include:
        return False
    excluded = any(keyword_matches(keyword, text) for keyword in rule.exclude_keywords)
    return not excluded


def is_all_day_event(event: Dict) -> bool:
    return "date" in (event.get("start") or {})


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
        if rule.all_day_only and not is_all_day_event(event):
            continue
        if matches_rule(rule, text):
            return rule
    return None


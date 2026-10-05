"""Skill pack management and error/context-driven semantic selection."""

from __future__ import annotations

import os
import re
from typing import List


class Skill:
    def __init__(
        self,
        name: str,
        description: str,
        signatures: list[str],
        trigger: str,
        body: str,
        path: str,
    ):
        self.name = name
        self.description = description
        self.signatures = signatures
        self.trigger = trigger
        self.body = body
        self.path = path

    def relevance_score(self, *texts: str) -> int:
        """Calculate relevance score against given contexts (prompt, error log, etc.)."""
        haystack = " ".join(t.lower() for t in texts if t)
        if not haystack:
            return 0

        score = 0
        # 1. Exact signature hit (+10)
        for sig in self.signatures:
            if sig.lower() in haystack:
                score += 10

        # 2. Trigger keywords (+5)
        if self.trigger:
            for word in re.split(r"[,、\s]+", self.trigger.lower()):
                if len(word) >= 2 and word in haystack:
                    score += 5

        # 3. Name tokens (+4)
        for token in self.name.lower().replace("-", " ").split():
            if len(token) >= 3 and token in haystack:
                score += 4

        # 4. Description tokens (+1)
        for token in set(self.description.lower().split()):
            if len(token) >= 4 and token in haystack:
                score += 1

        return score

    def matches(self, *texts: str) -> bool:
        return self.relevance_score(*texts) > 0

    def render(self, budget_chars: int = 4000) -> str:
        trimmed = self.body.strip()
        if len(trimmed) > budget_chars:
            trimmed = trimmed[:budget_chars] + "\n...[truncated for token budget]"
        return f'<skill name="{self.name}">\n{trimmed}\n</skill>'


def _split_front_matter(raw: str) -> tuple[dict, str]:
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2]
            meta = {}
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip("'\"")
            return meta, body
    return {}, raw


def _extract_bullet_items(body: str, label: str) -> list[str]:
    m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.*)", body)
    if not m:
        return []
    line = m.group(1).strip()
    items = re.findall(r"`([^`]+)`", line)
    if not items:
        items = [x.strip() for x in line.split(",") if x.strip()]
    return items


def _extract_bullet_text(body: str, label: str) -> str:
    m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.*)", body)
    return m.group(1).strip() if m else ""


def load_skills(skill_dir: str) -> list[Skill]:
    skills: list[Skill] = []
    if not os.path.isdir(skill_dir):
        return skills

    for entry in sorted(os.listdir(skill_dir)):
        path = os.path.join(skill_dir, entry, "SKILL.md")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
        except OSError:
            continue

        meta, body = _split_front_matter(raw)
        skills.append(
            Skill(
                name=meta.get("name", entry),
                description=meta.get("description", ""),
                signatures=_extract_bullet_items(body, "Log signatures"),
                trigger=_extract_bullet_text(body, "Trigger"),
                body=body,
                path=path,
            )
        )
    return skills


def select_skills(skills: list[Skill], *context: str, limit: int = 2) -> list[Skill]:
    """Rank skills by relevance score and return top matches."""
    scored = [(s, s.relevance_score(*context)) for s in skills]
    scored = [item for item in scored if item[1] > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in scored[:limit]]

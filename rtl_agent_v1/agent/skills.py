"""Skill pack management and error-driven selection."""

from __future__ import annotations

import os
import re


class Skill:
    def __init__(self, name: str, description: str, signatures: list[str],
                 trigger: str, body: str, path: str):
        self.name = name
        self.description = description
        self.signatures = signatures
        self.trigger = trigger
        self.body = body
        self.path = path

    def matches(self, *texts: str) -> bool:
        if not self.signatures:
            return False
        haystack = "\n".join(t.lower() for t in texts if t)
        return any(sig.lower() in haystack for sig in self.signatures)

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
                trigger="",
                body=body,
                path=path,
            )
        )
    return skills


def select_skills(skills: list[Skill], *context: str, limit: int = 2) -> list[Skill]:
    matched = [s for s in skills if s.matches(*context)]
    return matched[:limit]

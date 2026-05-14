#!/usr/bin/env python3
"""피드백 통합 스크립트 — 4축 검증 결과를 분석·분류·축적·에이전트 패치.

Usage:
    python scripts/consolidate_feedback.py output/{title}/
    python scripts/consolidate_feedback.py output/{title}/ --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERIFY_FILES = {
    "build": "_verify_build.md",
    "intent": "_verify_intent.md",
    "design": "_verify_design.md",
    "delivery": "_verify_delivery.md",
}

DESIGN_CATEGORIES = [
    "5-second-rule",
    "data-ink-ratio",
    "visual-hierarchy",
    "typography",
    "color-contrast",
    "whitespace",
    "cognitive-load",
    "motion",
]

DELIVERY_CATEGORIES = [
    "opening-hook",
    "three-act",
    "pacing",
    "rule-of-three",
    "concrete-language",
    "story-beats",
    "audience-reaction",
    "qa-prep",
]

BUILD_CATEGORIES = ["slide-sync", "asset-missing"]

INTENT_CATEGORIES = ["intent-omission", "intent-drift"]

# category -> list of (pattern, flags) tuples
_CLASSIFICATION_RULES: list[tuple[str, list[tuple[str, int]]]] = [
    ("5-second-rule", [(r"5[\-\s]?second", re.I), (r"5sec", re.I)]),
    ("data-ink-ratio", [(r"data[\-\s]?ink", re.I), (r"decorat", re.I)]),
    ("visual-hierarchy", [(r"hierarchy", re.I), (r"arrival\s*order", re.I)]),
    ("typography", [(r"font", re.I), (r"weight", re.I), (r"typogr", re.I), (r"line[\-\s]?height", re.I)]),
    ("color-contrast", [(r"contrast", re.I), (r"WCAG", 0)]),
    ("whitespace", [(r"whitespace", re.I), (r"content\s*area", re.I), (r"suffocati", re.I)]),
    ("cognitive-load", [(r"cognitive", re.I)]),
    ("motion", [(r"motion", re.I), (r"animation", re.I), (r"spin", re.I), (r"bounce", re.I)]),
    ("opening-hook", [(r"hook", re.I), (r"30\s*second", re.I), (r"30s", re.I)]),
    ("three-act", [(r"three[\-\s]?act", re.I), (r"act\s*ratio", re.I), (r"setup.*%", re.I)]),
    ("pacing", [(r"pacing", re.I), (r"pause", re.I), (r"chars/min", re.I), (r"speaking\s*time", re.I)]),
    ("rule-of-three", [(r"rule\s*of\s*three", re.I), (r"[≥>=]4\s*items", re.I), (r"4\s*items", re.I)]),
    ("concrete-language", [(r"abstract", re.I), (r"concrete", re.I), (r"innovative", re.I), (r"effective", re.I)]),
    ("story-beats", [(r"story\s*beat", re.I), (r"altitude", re.I), (r"callback", re.I)]),
    ("audience-reaction", [(r"audience", re.I), (r"empathy", re.I), (r"pushback", re.I)]),
    ("qa-prep", [(r"Q&A", re.I), (r"question", re.I)]),
    ("slide-sync", [(r"sync", re.I), (r"slide\s*count", re.I)]),
    ("asset-missing", [(r"404", 0), (r"asset", re.I)]),
    ("intent-omission", [(r"omission", re.I)]),
    ("intent-drift", [(r"drift", re.I), (r"distort", re.I)]),
]

# Special compound rules checked separately
_COMPOUND_RULES: list[tuple[str, list[str], list[str]]] = [
    # (category, all_of_patterns, any_of_patterns)
    ("cognitive-load", ["element"], ["≥4", ">=4"]),
    ("asset-missing", ["missing"], ["image", "video", "font"]),
]

CATEGORY_TO_AGENTS: dict[str, list[str]] = {}
for _cat in DESIGN_CATEGORIES:
    CATEGORY_TO_AGENTS[_cat] = ["design-critic.md", "design-director.md"]
for _cat in DELIVERY_CATEGORIES:
    CATEGORY_TO_AGENTS[_cat] = ["delivery-critic.md", "presentation-strategist.md"]
for _cat in BUILD_CATEGORIES:
    CATEGORY_TO_AGENTS[_cat] = ["build-verifier.md", "deck-builder.md"]
for _cat in INTENT_CATEGORIES:
    CATEGORY_TO_AGENTS[_cat] = ["intent-verifier.md", "deck-builder.md"]

LEARNED_PATTERNS_HEADER = (
    "## Learned patterns\n"
    "\n"
    "이 섹션은 피드백 자동 강화 시스템이 관리합니다. 수동 편집 금지.\n"
    "반복 패턴(2회+)이 자동 추가되며, 검증/계획 시 추가 체크리스트로 작동합니다.\n"
)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


class Issue(NamedTuple):
    severity: str  # "CRITICAL" or "ERROR"
    axis: str  # "build", "intent", "design", "delivery"
    text: str  # raw issue text
    category: str  # classified category


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_verify_file(path: Path, axis: str) -> list[Issue]:
    """Extract CRITICAL and ERROR issues from a _verify_*.md file."""
    if not path.exists():
        print(f"  [WARN] {path.name} 없음 — 건너뜀", file=sys.stderr)
        return []

    content = path.read_text(encoding="utf-8")
    issues: list[Issue] = []

    # Match sections: ### 🔴 CRITICAL or ### 🟠 ERROR (with optional trailing text)
    # Then collect numbered items until next heading or EOF
    section_pattern = re.compile(
        r"###\s*(?:🔴|:red_circle:)?\s*CRITICAL.*?\n(.*?)(?=\n###|\n##|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for m in section_pattern.finditer(content):
        for line in _extract_numbered_items(m.group(1)):
            issues.append(Issue("CRITICAL", axis, line, _classify(line, axis)))

    error_pattern = re.compile(
        r"###\s*(?:🟠|:orange_circle:)?\s*ERROR.*?\n(.*?)(?=\n###|\n##|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for m in error_pattern.finditer(content):
        for line in _extract_numbered_items(m.group(1)):
            issues.append(Issue("ERROR", axis, line, _classify(line, axis)))

    return issues


def _extract_numbered_items(block: str) -> list[str]:
    """Extract lines starting with a number (1. 2. etc.) or - bullet."""
    items: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if re.match(r"^\d+[\.\)]\s+", stripped) or re.match(r"^[-*]\s+", stripped):
            # Clean the marker
            cleaned = re.sub(r"^\d+[\.\)]\s+", "", stripped)
            cleaned = re.sub(r"^[-*]\s+", "", cleaned)
            if cleaned:
                items.append(cleaned)
    return items


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _classify(text: str, axis: str) -> str:
    """Classify an issue text into a category via keyword matching."""
    lower = text.lower()

    # Check compound rules first
    for cat, all_kw, any_kw in _COMPOUND_RULES:
        if all(k.lower() in lower for k in all_kw) and any(k.lower() in lower for k in any_kw):
            return cat

    # Check special "missing" in intent context
    if axis == "intent":
        if re.search(r"missing", lower) or re.search(r"omission", lower):
            return "intent-omission"
        if re.search(r"drift", lower) or re.search(r"distort", lower):
            return "intent-drift"

    # Standard rules
    for cat, patterns in _CLASSIFICATION_RULES:
        for pat, flags in patterns:
            if re.search(pat, text, flags):
                return cat

    return f"{axis}-unclassified"


# ---------------------------------------------------------------------------
# Lessons.md
# ---------------------------------------------------------------------------


def _append_lessons(
    feedback_dir: Path,
    deck_title: str,
    issues: list[Issue],
    today: str,
    dry_run: bool,
) -> None:
    lessons_path = feedback_dir / "lessons.md"

    rows = "\n".join(
        f"| {iss.severity} | {iss.category} | {_truncate(iss.text, 80)} |" for iss in issues
    )
    block = (
        f"\n## {deck_title} ({today})\n"
        f"\n"
        f"| Severity | Category | Issue |\n"
        f"|----------|----------|-------|\n"
        f"{rows}\n"
    )

    if dry_run:
        print(f"[DRY-RUN] {lessons_path} 에 추가할 내용:\n{block}")
        return

    feedback_dir.mkdir(parents=True, exist_ok=True)
    with lessons_path.open("a", encoding="utf-8") as f:
        f.write(block)


# ---------------------------------------------------------------------------
# Patterns.json
# ---------------------------------------------------------------------------


def _update_patterns(
    feedback_dir: Path,
    issues: list[Issue],
    today: str,
    dry_run: bool,
) -> dict[str, dict]:
    patterns_path = feedback_dir / "patterns.json"

    if patterns_path.exists():
        data: dict[str, dict] = json.loads(patterns_path.read_text(encoding="utf-8"))
    else:
        data = {}

    for iss in issues:
        cat = iss.category
        summary = _truncate(iss.text, 60)
        if cat not in data:
            data[cat] = {"count": 0, "last_seen": today, "issues": []}
        data[cat]["count"] += 1
        data[cat]["last_seen"] = today
        issue_list: list[str] = data[cat]["issues"]
        issue_list.append(summary)
        # Keep last 5
        if len(issue_list) > 5:
            data[cat]["issues"] = issue_list[-5:]

    if dry_run:
        print(f"[DRY-RUN] {patterns_path} 업데이트 내용:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        feedback_dir.mkdir(parents=True, exist_ok=True)
        patterns_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return data


# ---------------------------------------------------------------------------
# Agent patching
# ---------------------------------------------------------------------------


def _patch_agents(
    repo_root: Path,
    patterns: dict[str, dict],
    dry_run: bool,
) -> list[str]:
    """Patch agent files for categories with count >= 2. Returns patched filenames."""
    agents_dir = repo_root / ".claude" / "agents"
    if not agents_dir.is_dir():
        print(f"  [WARN] {agents_dir} 없음 — 에이전트 패치 건너뜀", file=sys.stderr)
        return []

    # Collect patches per agent file
    agent_patches: dict[str, list[str]] = {}  # filename -> list of pattern lines

    for cat, info in patterns.items():
        if info["count"] < 2:
            continue
        agent_files = CATEGORY_TO_AGENTS.get(cat, [])
        for agent_file in agent_files:
            if agent_file not in agent_patches:
                agent_patches[agent_file] = []
            line = (
                f"- [ ] **{cat} 강화** "
                f"({info['count']}회, 최근: {info['last_seen']}): "
                f"{_make_pattern_description(cat)}"
            )
            # Avoid duplicates within same agent
            if line not in agent_patches[agent_file]:
                agent_patches[agent_file].append(line)

    patched: list[str] = []
    for agent_file, lines in sorted(agent_patches.items()):
        agent_path = agents_dir / agent_file
        if not agent_path.exists():
            print(f"  [WARN] {agent_path} 없음 — 건너뜀", file=sys.stderr)
            continue

        content = agent_path.read_text(encoding="utf-8")

        # Find and replace the ## Learned patterns section
        # Match from "## Learned patterns" to next "## " heading or EOF
        lp_pattern = re.compile(
            r"(## Learned patterns\n)(.*?)(?=\n## |\Z)",
            re.DOTALL,
        )

        new_section = LEARNED_PATTERNS_HEADER + "\n" + "\n".join(lines) + "\n"

        if lp_pattern.search(content):
            new_content = lp_pattern.sub(new_section, content)
        else:
            print(
                f"  [WARN] {agent_file}: '## Learned patterns' 섹션 없음 — 건너뜀",
                file=sys.stderr,
            )
            continue

        if dry_run:
            print(f"[DRY-RUN] {agent_path} 패치:")
            print(new_section)
        else:
            agent_path.write_text(new_content, encoding="utf-8")

        patched.append(agent_file)

    return patched


def _make_pattern_description(category: str) -> str:
    """Generate a short enforcement description for a category."""
    descriptions: dict[str, str] = {
        "5-second-rule": "슬라이드당 메시지 1개 초과 시 자동 WARNING",
        "data-ink-ratio": "장식적 요소 비율 체크 강화",
        "visual-hierarchy": "시선 도착 순서 명시 검증",
        "typography": "폰트 weight 3개 이하 제한 검증",
        "color-contrast": "WCAG AA 대비율 자동 검증",
        "whitespace": "content area ratio > 70% 시 자동 ERROR",
        "cognitive-load": "슬라이드당 요소 4개 이상 시 자동 WARNING",
        "motion": "불필요한 애니메이션 사용 검증 강화",
        "opening-hook": "30초 내 훅 존재 여부 검증",
        "three-act": "3막 구조 비율 검증 강화",
        "pacing": "발표 시간/글자 수 비율 검증",
        "rule-of-three": "나열 항목 3개 이하 제한 검증",
        "concrete-language": "추상 표현 → 구체 표현 변환 검증",
        "story-beats": "스토리 비트 누락 검증 강화",
        "audience-reaction": "청중 반응 포인트 명시 검증",
        "qa-prep": "예상 질문 준비 여부 검증",
        "slide-sync": "HTML-스크립트 슬라이드 수 동기화 검증",
        "asset-missing": "에셋 경로 404 자동 검증 강화",
        "intent-omission": "plan.md 핵심 메시지 누락 검증 강화",
        "intent-drift": "plan.md 의도 왜곡 검증 강화",
    }
    return descriptions.get(category, f"{category} 패턴 반복 — 추가 검증 필요")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _find_repo_root(deck_dir: Path) -> Path:
    """Find the repo root by looking for .claude/ directory.

    Search order:
    1. Walk up from deck_dir
    2. Walk up from cwd
    3. Walk up from script location
    """
    for start in [deck_dir.resolve(), Path.cwd().resolve(), Path(__file__).resolve().parent]:
        current = start
        for _ in range(10):
            if (current / ".claude" / "agents").is_dir():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent
    # Fallback: cwd
    return Path.cwd()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="4축 검증 결과를 통합·분류·축적·에이전트 패치",
    )
    parser.add_argument(
        "deck_dir",
        type=Path,
        help="deck 출력 디렉토리 (예: output/거울을_마주보다/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 파일 쓰기 없이 결과만 출력",
    )
    args = parser.parse_args()

    deck_dir: Path = args.deck_dir.resolve()
    dry_run: bool = args.dry_run

    if not deck_dir.is_dir():
        print(f"[ERROR] 디렉토리 없음: {deck_dir}", file=sys.stderr)
        sys.exit(1)

    deck_title = deck_dir.name
    today = date.today().isoformat()
    repo_root = _find_repo_root(deck_dir)
    feedback_dir = repo_root / "feedback"

    # 1. Parse all verify files
    all_issues: list[Issue] = []
    for axis, filename in VERIFY_FILES.items():
        path = deck_dir / filename
        issues = _parse_verify_file(path, axis)
        all_issues.extend(issues)

    if not all_issues:
        print("피드백 통합: CRITICAL 0, ERROR 0 — 이슈 없음")
        return

    critical_count = sum(1 for i in all_issues if i.severity == "CRITICAL")
    error_count = sum(1 for i in all_issues if i.severity == "ERROR")

    # 2. Append to lessons.md
    _append_lessons(feedback_dir, deck_title, all_issues, today, dry_run)

    # 3. Update patterns.json
    patterns = _update_patterns(feedback_dir, all_issues, today, dry_run)

    # 4. Patch agents (count >= 2)
    patched = _patch_agents(repo_root, patterns, dry_run)

    # 5. Summary
    new_patterns = [
        f"{cat} (-> {info['count']}회)"
        for cat, info in patterns.items()
        if info["count"] >= 2
    ]

    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{prefix}피드백 통합 완료: CRITICAL {critical_count}, ERROR {error_count}")
    if new_patterns:
        print(f"{prefix}신규 패턴: {', '.join(new_patterns)}")
    if patched:
        print(f"{prefix}패치된 에이전트: {', '.join(patched)}")


if __name__ == "__main__":
    main()

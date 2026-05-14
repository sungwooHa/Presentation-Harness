---
name: feedback-consolidator
description: "Phase 3 완료 후 검증 결과를 누적 피드백으로 통합하는 스킬. CRITICAL/ERROR를 카테고리별로 분류 → feedback/lessons.md에 누적 → patterns.json 갱신 → 반복 패턴(2회+)을 해당 agent의 Learned patterns 섹션에 자동 패치. 트리거: Phase 3 완료 후 자동, '/feedback-consolidate', '피드백 통합'."
---

# Feedback Consolidator — Phase 3.5 자동 피드백 통합

Phase 3 (VERIFY) 완료 후 CRITICAL 또는 ERROR가 1건 이상이면 자동 실행.

## 실행 조건

- Phase 3의 4축 검증 완료
- `_verify_build.md`, `_verify_intent.md`, `_verify_design.md`, `_verify_delivery.md` 중 1개 이상 존재
- CRITICAL 또는 ERROR가 1건 이상

## 실행

```bash
python scripts/consolidate_feedback.py output/{title}/
```

## 결과

1. **feedback/lessons.md** — 이번 검증 결과 append
2. **feedback/patterns.json** — 카테고리별 count 갱신
3. **agent .md 패치** — count >= 2인 패턴 → 해당 agent의 `## Learned patterns` 섹션 자동 업데이트

## 사용자 확인

결과 1줄 요약 후 사용자에게 commit/push 확인:

```
피드백 통합 완료: CRITICAL N, ERROR M
신규/갱신 패턴: {category} (→ {count}회)
패치된 에이전트: {agent1}.md, {agent2}.md

커밋하시겠습니까?
  git add feedback/ .claude/agents/
  git commit -m "feedback: {title} 검증 누적 (CRITICAL N, ERROR M)"
  git push
```

사용자 승인 시에만 commit + push.

## 수동 실행

```bash
# 특정 덱의 피드백 통합
python scripts/consolidate_feedback.py output/분기_OKR_리뷰/

# 드라이런 (변경 없이 확인만)
python scripts/consolidate_feedback.py output/분기_OKR_리뷰/ --dry-run
```

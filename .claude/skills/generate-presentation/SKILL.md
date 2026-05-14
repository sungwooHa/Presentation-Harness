---
name: generate-presentation
description: "발표자료 풀 파이프라인 오케스트레이터 (3-stage harness, 강한 게이트). Phase 1 PLAN(presentation-strategist + design-director → plan.md → 사용자 승인 게이트) → Phase 2 BUILD(deck-builder + asset-curator) → Phase 3 VERIFY(4축 병렬: build-verifier ∥ intent-verifier ∥ design-critic ∥ delivery-critic) → Phase 3.5 FEEDBACK(자동 누적). 검증은 엄격 — 4축 중 1축이라도 CRITICAL이면 진행 불가. 'output/{title}/reference/'에 자료 드롭 가능; 비어있어도 OK. 트리거: '발표자료 만들어줘', '/generate-presentation', '템플릿으로 발표 만들어'."
---

# Generate Presentation — Full Pipeline Orchestrator (3-stage harness)

Use `templates/` as the golden pattern, **anyone can clone and produce a top-tier deck** through this harness.
3 stages + feedback loop × strong gates — define intent → build → 4-axis strict verification → feedback consolidation.

## Outputs (3-piece set)

| File | Role | Required |
|------|------|----------|
| `output/{title}/index.html` | Main slide viewer (1920x1080, audience) | yes |
| `output/{title}/스크립트_화면.html` | Presenter script viewer (BroadcastChannel sync) | yes |
| `output/{title}/index.pptx` | Audience PPT (HTML screenshot + notes embed) | optional |

## Workflow (3-stage + feedback)

```
User input (topic) + (optional) output/{title}/reference/ material
  |
Phase 0: Reference scan
  Recursive scan of output/{title}/reference/ → index
  Empty → "no reference material" 1-line notice, pass through
  |
Phase 1: PLAN
  presentation-strategist  ||  design-director
       |
       _workspace/plan.md (the two outputs merged)
       |
       USER APPROVAL GATE — block here
       | (after approval only)

Phase 2: BUILD
  asset-curator → deck-builder
       |
       output/{title}/index.html, 스크립트_화면.html, CLAUDE.md
       |
       (optional) python scripts/build_pptx_screenshot.py → index.pptx
       |

Phase 3: VERIFY (4 axes parallel, strict)
  build-verifier || intent-verifier || design-critic || delivery-critic
       |
       _verify_build / _intent / _design / _delivery .md
       |
       4 axes all PASS → Phase 3.5
       Any 1 axis CRITICAL → user 4-choice prompt
       |

Phase 3.5: FEEDBACK CONSOLIDATION (auto)
  python scripts/consolidate_feedback.py output/{title}/
       |
       feedback/lessons.md updated
       feedback/patterns.json updated
       agent .md patched (if count >= 2)
       |
       Summary + commit/push confirmation
```

## Phase 0: Reference scan

Recursive scan of `output/{title}/reference/`:
```bash
find "output/{title}/reference" -type f \
  ! -name 'README.md' ! -name '.DS_Store' ! -name '.gitkeep'
```

Empty → 1-line notice and pass (no error). Record index in `_workspace/00_input.md`.

## Phase 1: PLAN

### Parallel calls

```
[Agent: presentation-strategist]
  Input: user topic, reference index
  Output: _workspace/plan_strategy.md (audience, intent, message, story, slide skeleton, criteria)

[Agent: design-director]
  Input: user topic, reference index, plan_strategy.md
  Output: _workspace/plan_design.md (visual direction, color, type, pattern mapping, criteria)
```

Merge the two into **a single `_workspace/plan.md`**. Sections 1-7 from strategist + section 8 from design-director.

### User approval gate (most important)

Show plan.md to the user:

```
plan.md 작성 완료. 검토 부탁드립니다:

  output/{title}/_workspace/plan.md

핵심:
  - 의도(감정/생각/행동): {3 axes one line each}
  - 핵심 메시지: "{One Sentence}"
  - 슬라이드 N장 / 약 {분} / Act {수} 구조
  - 비주얼 톤: {choice}
  - 검증 기준 4축 합계 {N}개 항목

선택하세요:
  1) 승인 — Phase 2 (빌드) 진행
  2) 수정 — 어디를 수정할지 알려주세요 (strategist 또는 design-director 재호출)
  3) 중단

선택:
```

**Do not advance to Phase 2 until response 1) is received.** Most important gate.

## Phase 2: BUILD

### Parallel → sequential

```
[Agent: asset-curator]   ← first (deck-builder needs asset paths)
  Input: plan.md, reference/
  Output: output/{title}/assets/{images,videos,charts}/, _workspace/asset_log.md

[Agent: deck-builder]    ← after asset-curator
  Input: plan.md, asset_log.md, templates/
  Output: output/{title}/index.html, 스크립트_화면.html, CLAUDE.md, _workspace/build_log.md
```

### PPTX build (optional)

If user did not opt out, build by default:

```bash
python scripts/build_pptx_screenshot.py output/{title}/index.html
# → output/{title}/index.pptx
```

If Playwright missing, skip PPTX with notice:
```
pip install playwright python-pptx beautifulsoup4 Pillow
playwright install chromium
```

## Phase 3: VERIFY (4 axes parallel, strict)

**Call 4 agents simultaneously** (4 Tasks in one message):

```
[Agent: build-verifier]
  Target: output/{title}/ (HTML + PPTX combined check)
  Output: output/{title}/_verify_build.md

[Agent: intent-verifier]
  Target: plan.md vs output/{title}/index.html, 스크립트_화면.html
  Output: output/{title}/_verify_intent.md

[Agent: design-critic]
  Target: output/{title}/index.html (Playwright screenshot + DOM analysis)
  Authority: plan.md design criteria + Tufte/Reynolds/Bringhurst 8 principles
  Output: output/{title}/_verify_design.md

[Agent: delivery-critic]
  Target: output/{title}/스크립트_화면.html (BeautifulSoup text analysis)
  Authority: plan.md intent/story criteria + Anderson/Gallo/Duarte 8 principles
  Output: output/{title}/_verify_delivery.md
```

### Pass criteria (strict)

| Result | 4-axis state | Action |
|--------|-------------|--------|
| **PASS** | All 4 axes CRITICAL == 0 | Phase 3.5 → deliver |
| **ERROR only** | CRITICAL 0, ERROR present | Phase 3.5 → show reports, ask user |
| **FAIL** | Any 1 axis CRITICAL >= 1 | Force user 4-choice |

### 4-choice (on FAIL)

```
[검증] FAIL — {per-axis CRITICAL count}
  - build-verifier:    N
  - intent-verifier:   N
  - design-critic:     N
  - delivery-critic:   N

상세: output/{title}/_verify_{axis}.md

선택하세요:
  1) 자동 수정 시도 — 알려진 패턴이면 패치 후 재검증 (Phase 2로 회귀)
  2) 무시하고 진행 — 검증 실패 표시한 채 산출물 전달 (권장 X)
  3) 중단하고 수동 수정 — 작업 중단, 사용자가 직접 수정 (기본값)
  4) 재생성 — Phase 1부터 다시 (덱 전체 재작업, plan.md 재검토)

선택 (1-4):
```

**Default 3) 중단**. Branch only on explicit 1/2/4 choice.

### Per-choice action

| Choice | Action |
|--------|--------|
| 1) Auto-fix | Try known patches → Phase 3 re-run. Fall back to 3) on unknown patterns |
| 2) Ignore | Deliver + explicit failure report |
| 3) Stop | Show report paths and end |
| 4) Regenerate | Backup `_workspace/` → call Phase 1 again |

## Phase 3.5: FEEDBACK CONSOLIDATION (auto)

Phase 3 완료 후 CRITICAL 또는 ERROR가 1건 이상이면 자동 실행:

```bash
python scripts/consolidate_feedback.py output/{title}/
```

**동작**:
1. `_verify_*.md` 파싱 → CRITICAL/ERROR 추출
2. 카테고리 자동 분류 (design/delivery/build/intent)
3. `feedback/lessons.md`에 이번 검증 결과 append
4. `feedback/patterns.json` 갱신 (count 증가)
5. count >= 2인 패턴 → 해당 agent .md의 `## Learned patterns` 섹션 자동 패치

결과 1줄 요약 후 사용자에게 commit/push 확인:
```
git add feedback/ .claude/agents/
git commit -m "feedback: {title} 검증 누적 (CRITICAL N, ERROR M)"
git push
```

## Input defaults

If unspecified:
- Audience: general business audience
- Time: 15 min (15-25 slides)
- Format: report/proposal
- PPTX build: ON by default
- reference/: empty OK

## Repeat-use scenarios

```bash
# New deck
/generate-presentation 분기 OKR 리뷰

# Re-verify only
/generate-presentation --verify-only output/2026Q1_OKR_리뷰

# Re-build PPTX only
python scripts/build_pptx_screenshot.py output/2026Q1_OKR_리뷰/index.html

# Re-build after editing plan.md
/generate-presentation --rebuild output/2026Q1_OKR_리뷰
```

## Agent roster (8)

### Phase 1 (PLAN, 2)
- `presentation-strategist` — content, audience, intent, story, criteria
- `design-director` — visual concept, pattern mapping, criteria

### Phase 2 (BUILD, 2)
- `asset-curator` — image/video/chart curation
- `deck-builder` — HTML slides + script markup

### Phase 3 (VERIFY, 4 parallel)
- `build-verifier` — technical integrity (HTML/PPTX build)
- `intent-verifier` — plan.md vs output match
- `design-critic` — design quality (Tufte/Reynolds/Bringhurst)
- `delivery-critic` — speaking quality (Anderson/Gallo/Duarte)

## Core principles

- **plan.md = authority** — Phase 2/3 both follow plan.md
- **User approval gate = once** — after Phase 1, plan.md approval
- **Verify is strict** — any 1 axis CRITICAL = no pass
- **No self-critique** — strategist/director do not critique; critics are separate personas
- **Self-contained** — no external URL refs; resolve within reference/ and assets/
- **Feedback loop** — every build strengthens the next through cumulative patterns

## Output language

User-facing messages in Korean. Internal agent communication may be English. Final deck content in Korean.

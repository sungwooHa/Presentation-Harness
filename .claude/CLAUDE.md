# Presentation Harness — 자급자족 발표자료 생성 시스템

## 작업 원칙

전역 행동 지침을 따른다 → `~/.claude/CLAUDE.md` 의 "작업 원칙" 섹션 참조.

### 본 프로젝트의 명시적 예외

- **더미 데이터 + 플레이스홀더**: 데이터 부재 시 더미 + 플레이스홀더 표시는 *명시적으로 인가된 가정*이다. 전역 "Think Before Coding"의 "혼자 가정 말라" 조항에 어긋나지 않음 (가정 사실을 플레이스홀더로 표시하므로).
- **풀 에이전트 파이프라인**: 사용자가 "발표자료 만들어줘"로 진입하면 3단계 콘텐츠 + 빌드 + 검증 + 피드백 협업은 *요청된 작업 범위*다. 전역 "Simplicity First"의 "요청 범위 초과 금지" 위반 아님.
- **기본값 적용**: 청중/시간 미지정 시 "일반 비즈니스 청중, 15분"은 인가된 기본값. 적용 사실을 1줄로 알린다.

## 프로젝트 개요

에이전트 팀이 협업해서 발표자료(HTML 슬라이드 + 발표자 스크립트뷰어 + 선택적 PPTX) 3종 세트를 만드는 자급자족 시스템. Clone → 발표 생성 → 검증 피드백이 agent 지침에 자동 반영되어 최소 품질이 점진적으로 상승.

## 디렉토리 구조

```
Presentation-Harness/
├── .claude/
│   ├── CLAUDE.md                      ← 이 파일
│   ├── agents/                        ← 8 agents (3-stage harness)
│   │   ├── presentation-strategist.md — 청중·의도·메시지·스토리·검증 기준
│   │   ├── design-director.md         — 비주얼 톤·컬러·타이포·패턴 매핑
│   │   ├── asset-curator.md           — 이미지·비디오·차트 큐레이션
│   │   ├── deck-builder.md            — HTML 슬라이드 + 스크립트 마크업
│   │   ├── build-verifier.md          — 기술 무결성
│   │   ├── intent-verifier.md         — plan.md vs 산출물 매칭
│   │   ├── design-critic.md           — 디자인 품질
│   │   └── delivery-critic.md         — 발표 품질
│   └── skills/
│       ├── generate-presentation/     — 3-stage harness 오케스트레이터
│       ├── slide-layout-patterns/     — 20가지 레이아웃 패턴
│       ├── data-visualization-guide/  — 차트 선택 가이드
│       └── feedback-consolidator/     — 피드백 자동 통합
│
├── templates/
│   ├── index.html                     — 메인 슬라이드 뷰어 셸
│   ├── 스크립트_화면.html              — 발표자 스크립트 뷰어 셸
│   └── CLAUDE.md                      — deck 내부 작업 규칙
│
├── assets/fonts/                      — Paperlogy 8종 .otf (Git LFS)
│
├── scripts/
│   ├── build_pptx_screenshot.py       — HTML → PPTX (스크린샷+노트)
│   └── consolidate_feedback.py        — 피드백 추출 + agent 패치
│
├── feedback/
│   ├── lessons.md                     — 누적 피드백 (Git 추적)
│   └── patterns.json                  — 반복 패턴 집계 (Git 추적)
│
├── reference/                         — 참조 자료 드롭존 (.gitignore 내용물)
├── output/                            — 생성된 발표자료 (.gitignore)
└── _workspace/                        — 에이전트 산출물 (.gitignore)
```

## 사용법

### 풀 파이프라인 (3-stage harness + 피드백)
```
/generate-presentation [주제]
또는
발표자료 만들어줘: [주제]
```
→ Phase 1 PLAN → 사용자 승인 → Phase 2 BUILD → Phase 3 VERIFY → Phase 3.5 FEEDBACK → 산출물

산출물 위치: `output/{title}/index.html`, `스크립트_화면.html`, `index.pptx`(선택)

### 단독: HTML이 이미 있을 때 PPTX만 생성
```
python scripts/build_pptx_screenshot.py output/{title}/index.html
```

선행 조건:
```
pip install -r requirements.txt
playwright install chromium
```

### 피드백 수동 통합
```
python scripts/consolidate_feedback.py output/{title}/
```

## 워크플로우 (3-stage harness + 피드백 루프)

```
사용자 입력 (주제) + (선택) reference/ 자료
  ↓
Phase 0: 참조 자료 스캔
  ↓
Phase 1: PLAN
  presentation-strategist  ∥  design-director
       ↓
       _workspace/plan.md → 사용자 승인 게이트
       ↓
Phase 2: BUILD
  asset-curator → deck-builder
       ↓
       output/{title}/ (HTML + 스크립트 + PPTX)
       ↓
Phase 3: VERIFY (4축 병렬)
  build-verifier ∥ intent-verifier ∥ design-critic ∥ delivery-critic
       ↓
Phase 3.5: FEEDBACK CONSOLIDATION
  consolidate_feedback.py → lessons.md + patterns.json + agent 패치
       ↓
       commit/push → 다음 발표 시 강화된 agent 지침
```

## 피드백 자동 강화 메커니즘

매 발표의 CRITICAL/ERROR가 agent 체크리스트에 누적. 같은 실수가 반복(2회+)되면:
- **계획 단계**: director/strategist의 `## Learned patterns`에서 사전 차단
- **검증 단계**: critic/verifier에서 더 엄격하게 잡힘

피드백 흐름:
1. Phase 3에서 `_verify_*.md` 생성
2. `consolidate_feedback.py`가 CRITICAL/ERROR 추출 → 카테고리 분류
3. `feedback/lessons.md`에 누적, `feedback/patterns.json`에 count 갱신
4. count >= 2인 패턴 → 해당 agent `.md`의 `## Learned patterns` 섹션 자동 패치
5. git push → 다음 clone 시 강화된 지침

## 산출물

### Phase 0~1 (계획, _workspace/)

| 파일 | 내용 |
|------|------|
| `_workspace/00_input.md` | 사용자 입력 + reference 인덱스 |
| `_workspace/plan_strategy.md` | presentation-strategist 산출 |
| `_workspace/plan_design.md` | design-director 산출 |
| **`_workspace/plan.md`** | **두 산출 통합 — 사용자 승인 게이트 대상** |

### Phase 2 (빌드, output/{title}/)

| 파일 | 역할 | 필수 |
|------|------|------|
| `index.html` | 메인 슬라이드 뷰어 (1920x1080) | yes |
| `스크립트_화면.html` | 발표자 스크립트 뷰어 | yes |
| `CLAUDE.md` | deck 내부 작업 규칙 | yes |
| `index.pptx` | 청중 배포용 PPT | optional |
| `assets/fonts/` | Paperlogy 8종 weight .otf | yes |

### Phase 3 (4축 검증)

| 파일 | 내용 |
|------|------|
| `_verify_build.md` | 기술 무결성 |
| `_verify_intent.md` | plan.md vs 산출물 매칭 |
| `_verify_design.md` | 디자인 품질 비평 |
| `_verify_delivery.md` | 발표 품질 비평 |

## PPTX 산출 철학

- HTML이 정답. PPTX는 청중 배포/오프라인 보조.
- 슬라이드 본체 = HTML 스크린샷 PNG 풀블리드 임베드 (텍스트 편집 불가, 의도된 트레이드오프)
- 발표 노트 = python-pptx의 notes_slide 텍스트 (검색·복사 가능)

## 검증 실패 처리 정책

4축 검증 중 **1축이라도** CRITICAL 발생 시:
- **자동 진행 금지** — 항상 사용자에게 4지선다
- **기본값**: 3) 중단하고 수동 수정
- 검증은 엄격함을 우선한다 — 친절한 비평이 아니라 정확한 비평

## 산출물 폴더 규칙

- 모든 산출물은 반드시 `output/{title}/` 폴더 안에 생성한다
- 루트에 `index.html`, `스크립트_화면.html` 등을 직접 생성 금지
- 폴더 구조:
  ```
  output/{title}/
  ├── index.html
  ├── 스크립트_화면.html
  ├── CLAUDE.md
  ├── assets/fonts/
  ├── assets/images/
  └── index.pptx (선택)
  ```

## 완료 필수 프로세스

작업 완료 시 아래 프로세스를 **반드시** 순서대로 수행한다. 생략 불가.

1. **피드백 통합**: Phase 3 검증 결과에서 CRITICAL/ERROR 추출 → `feedback/lessons.md` 누적, `feedback/patterns.json` 갱신
2. **에이전트 강화**: 반복 패턴(2회+)을 해당 agent `.md`의 `## Learned patterns`에 패치
3. **템플릿 반영**: 범용 교훈은 `templates/CLAUDE.md`, `templates/index.html` 등 템플릿에도 반영
4. **git push**: 변경사항 커밋 후 `git push origin main` — 다음 clone에 강화된 지침 반영

> 사용자가 "완료", "끝", "다 됐다" 등 완료 신호를 보내면 이 프로세스를 자동 시작한다.

## 핵심 규칙

- 모든 출력은 한국어
- 1슬라이드 1메시지 원칙
- 데이터가 없으면 더미 데이터 + 플레이스홀더 표시
- 청중/시간 미지정 시: 일반 비즈니스 청중, 15분(15~25 슬라이드) 기본값
- 폰트는 `assets/fonts/`의 Paperlogy 8종 weight 그대로 사용

## 필수 환경변수

에이전트 팀 기능 사용 시:
```
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

## Clone 워크플로우

```bash
# 1. 클론
git clone git@github.com:sungwooHa/Presentation-Harness.git "발표제목"

# 2. 참조자료 드롭
cp 참고자료/* "발표제목/reference/"

# 3. 발표 생성
cd "발표제목"
claude  # → "발표자료 만들어줘: [주제]"

# 4. Phase 1~3 자동 진행 → Phase 3.5 피드백 → push
# (push가 원본 repo를 강화 → 다음 clone에 반영)
```

# Presentation Harness

자급자족 발표자료 생성 시스템. Claude Code의 에이전트 팀이 협업하여 HTML 슬라이드 + 발표자 스크립트 + PPTX 3종 세트를 만들고, 검증 피드백이 누적되어 품질이 점진적으로 상승합니다.

## 사전 조건

- [Claude Code](https://claude.com/claude-code) CLI
- Python 3.10+
- Git LFS (폰트 파일 관리)

```bash
pip install -r requirements.txt
playwright install chromium
```

## 사용법

### 1. 클론

```bash
git clone git@github.com:sungwooHa/Presentation-Harness.git "발표제목"
cd "발표제목"
```

### 2. 참조자료 준비 (선택)

```bash
cp 참고자료/* reference/
```

### 3. 발표 생성

```bash
claude  # Claude Code 실행
# → "발표자료 만들어줘: [주제]"
```

### 4. 워크플로우

```
Phase 1: PLAN — 전략(strategist) + 디자인(director) → plan.md → 사용자 승인
Phase 2: BUILD — 에셋(curator) + 빌드(builder) → HTML + 스크립트 + PPTX
Phase 3: VERIFY — 4축 병렬 검증 (빌드/의도/디자인/발표)
Phase 3.5: FEEDBACK — 피드백 누적 → agent 지침 자동 강화
```

### 5. 산출물

```
output/{title}/
├── index.html          ← 메인 슬라이드 (1920x1080)
├── 스크립트_화면.html   ← 발표자 스크립트 뷰어
├── index.pptx          ← 청중 배포용 PPT (선택)
└── assets/             ← 이미지, 비디오, 폰트
```

## 에이전트 구성 (8개)

| Phase | Agent | 역할 |
|-------|-------|------|
| PLAN | presentation-strategist | 청중, 의도, 메시지, 스토리, 검증 기준 |
| PLAN | design-director | 비주얼 톤, 컬러, 타이포, 패턴 매핑 |
| BUILD | asset-curator | 이미지/비디오/차트 큐레이션 |
| BUILD | deck-builder | HTML 슬라이드 + 스크립트 마크업 |
| VERIFY | build-verifier | 기술 무결성 (HTML+PPTX) |
| VERIFY | intent-verifier | plan.md vs 산출물 매칭 |
| VERIFY | design-critic | 디자인 품질 (Tufte/Reynolds/Bringhurst) |
| VERIFY | delivery-critic | 발표 품질 (Anderson/Gallo/Duarte) |

## 피드백 자동 강화

매 발표의 검증 결과(CRITICAL/ERROR)가 `feedback/`에 누적됩니다. 같은 패턴이 2회 이상 반복되면 해당 agent의 `## Learned patterns` 섹션에 자동 추가되어, 다음 발표에서는 계획 단계에서 사전 차단되고 검증 단계에서 더 엄격하게 잡힙니다.

```bash
# 수동 피드백 통합
python scripts/consolidate_feedback.py output/{title}/

# 드라이런
python scripts/consolidate_feedback.py output/{title}/ --dry-run
```

## PPTX 단독 빌드

HTML이 이미 있을 때:

```bash
python scripts/build_pptx_screenshot.py output/{title}/index.html
```

## 환경변수

에이전트 팀 기능 사용 시:
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

## 라이선스

Private repository. Paperlogy 폰트는 PT&의 라이선스를 따릅니다.

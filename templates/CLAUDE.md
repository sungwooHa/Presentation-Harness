# {{DECK_TITLE}} — Deck Rules

## 기본 정보

- **제목**: {{DECK_TITLE}}
- **부제**: {{DECK_SUBTITLE}}
- **발표자**: {{PRESENTER}}
- **일자**: {{DECK_DATE}}
- **청중**: {{AUDIENCE}}
- **시간**: {{DURATION}}
- **슬라이드 수**: {{SLIDE_COUNT}}
- **목적**: {{PURPOSE}}

## 산출물 구조

| 파일 | 역할 |
|------|------|
| `index.html` | 메인 슬라이드 뷰어 (1920x1080, F=전체화면, P=발표자뷰) |
| `스크립트_화면.html` | 발표자 스크립트 뷰어 (BroadcastChannel sync) |
| `index.pptx` | 청중 배포용 PPT (선택) |
| `assets/fonts/` | Paperlogy 8종 weight .otf |
| `assets/images/` | 슬라이드 이미지 에셋 |
| `assets/videos/` | 슬라이드 비디오 에셋 |

## 편집 규칙

- index.html 수정 시 스크립트_화면.html과 1:1 sync 유지 필수
- 슬라이드 추가/삭제 시 양쪽 파일 동시 수정
- 폰트는 assets/fonts/의 Paperlogy만 사용
- 외부 URL 참조 금지 (자급자족 원칙)

## PPTX 재빌드

```bash
python scripts/build_pptx_screenshot.py index.html
```

# 📄 Paper2Web Archive

AI 기술을 활용해 학술 논문을 읽기 쉬운 웹 인터페이스(Paper2Web) 포맷으로 변환하여 모아두는 아카이브 저장소입니다.

## 🌟 주요 특징

- **자동 인덱싱:** 새로운 논문이 추가되면 GitHub Actions가 자동으로 메인 페이지(`index.html`)를 생성합니다.
- **다국어 지원:** `kr`, `en` 등 언어별 폴더를 자동으로 감지하고 필터링 기능을 제공합니다.
- **실시간 검색:** 논문 제목을 기반으로 원하는 자료를 빠르게 찾을 수 있습니다.
- **반응형 디자인:** 모바일과 데스크탑 어디서든 최적화된 독서 경험을 제공합니다.

## 📂 저장소 구조

```text
.
├── kr/               # 한국어 번역 논문
├── en/               # 영어 원문 논문
├── .github/
│   ├── scripts/      # 인덱스 자동 생성 스크립트
│   └── workflows/    # GitHub Actions 배포 설정
└── README.md
```

## 🚀 논문 추가 방법

새로운 논문을 추가하려면 다음 단계를 따르세요:

1.  언어에 맞는 폴더(`kr`, `en` 등)에 변환된 `.html` 파일을 넣습니다.
    *   새로운 언어 폴더를 만들어도 자동으로 인식됩니다 (예: `jp`, `cn`).
2.  `git commit` 후 `push` 합니다.
3.  1~2분 뒤 GitHub Actions가 자동으로 배포를 완료하면 메인 페이지에 새 논문이 나타납니다.

## 🛠️ 기술 스택

- **Frontend:** Semantic HTML5, Vanilla CSS (Lora, DM Sans WebFonts)
- **Automation:** Python 3.10, GitHub Actions
- **Deployment:** GitHub Pages (Static Site Deployment)

---
## 🔗 관련 프로젝트

이 저장소의 논문 포맷은 [Paper2Web](https://github.com/Taepoung/paper2web) 프로젝트의 스킬을 사용하여 생성되었습니다. 논문의 원문 구조를 해치지 않으면서도 최적의 웹 가독성을 제공하는 것을 목표로 합니다.

---
*이 프로젝트는 연구자의 논문 리딩 경험을 개선하기 위해 관리되고 있습니다.*
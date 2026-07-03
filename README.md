# DocuGuard AI

DocuGuard AI는 문서와 웹페이지 증거를 빠르게 검토하는 Streamlit 기반 AI 포렌식 MVP입니다. 법적 또는 최종 진위 판단을 내리는 서비스가 아니라, 문서와 웹페이지에서 추가 검토가 필요한 후보를 빠르게 선별하는 해커톤 제출용 도구입니다.

## 주요 기능

- Landing Page와 MVP 분석 화면 분리
- JPG, PNG, PDF 문서 업로드 및 분석
- PDF 전체 페이지 미리보기 및 페이지별 분석
- ELA, 국소 노이즈 불일치, 블러 차이, 배경 질감 불일치 기반 문서 위조 후보 탐지
- 분석 결과 이미지와 의심 포인트 요약 표시
- 최대 10개 분석 문서를 보관하는 Document Vault
- 웹페이지 캡처 이미지 분석
- URL 접속 가능 여부, 리다이렉트, 도메인, HTTPS, 페이지 제목, 의심 키워드 검토
- 웹 증거 신뢰도 점수 및 위험도 리포트

## 프로젝트 구조

```text
app.py              # Streamlit Community Cloud entry point
document_vault.py   # 문서 보관함 데이터 처리
forensics.py        # 문서 이미지/PDF 포렌식 분석
web_forensics.py    # URL 및 웹페이지 증거 검토
sample_generator.py # 샘플 문서 생성
requirements.txt    # Python dependencies
README.md
```

## 실행 파일

Streamlit Community Cloud의 Main file path는 다음 파일을 사용합니다.

```text
app.py
```

## 로컬 설치

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 로컬 실행

프로젝트 루트에서 실행합니다.

```bash
streamlit run app.py
```

Streamlit 실행 파일이 PATH에 없다면 다음 명령을 사용합니다.

```bash
python -m streamlit run app.py
```

## Streamlit Community Cloud 배포

Streamlit Community Cloud에서 새 앱을 만들 때 아래 값을 입력합니다.

```text
Repository: https://github.com/venus5406-glitch/ai-document-forensic
Branch: main
Main file path: app.py
```

배포 전 GitHub에 변경 사항을 업로드합니다.

```bash
git add .
git commit -m "Prepare Streamlit Cloud deployment"
git push origin main
```

## 해커톤 제출용 설명

DocuGuard AI는 문서와 웹페이지의 위조 가능성을 AI 포렌식 관점에서 빠르게 검토하는 보안 SaaS MVP입니다. 사용자는 문서 파일 또는 웹 증거를 입력하고, 시스템은 이미지 포렌식 신호와 URL 검토 결과를 바탕으로 의심 영역, 신뢰도, 위험 요약을 제공합니다. 분석 완료 문서는 최대 10개까지 보관함에 저장되어 결과를 다시 확인할 수 있습니다.

## 배포 플랫폼

이 프로젝트는 Streamlit Python 앱입니다. Vercel보다 Streamlit Community Cloud에 배포하는 것이 적합합니다. Streamlit Cloud는 GitHub 저장소를 연결하면 `requirements.txt`를 설치하고 `app.py`를 실행하여 공개 URL을 생성합니다.

## 참고

- URL 검증은 API 키 없이 `requests`와 `BeautifulSoup`으로 동작합니다.
- PDF 처리는 `PyMuPDF` 패키지의 `fitz` 모듈을 사용합니다.
- OpenCV는 Streamlit Cloud 환경에 맞게 `opencv-python-headless`를 사용합니다.
- 현재 MVP 결과는 최종 법적 판단이 아니라 추가 검토 후보를 선별하는 참고 정보입니다.

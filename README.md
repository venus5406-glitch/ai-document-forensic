# DocuGuard AI

DocuGuard AI는 문서와 웹페이지 증거를 검토하는 Streamlit 기반 해커톤 MVP입니다. 법적 또는 최종 진위 판단을 내리는 서비스가 아니라, 추가 검토 후보를 빠르게 선별하는 도구입니다.

## 주요 기능

- 문서 위조 탐지 모드
- 웹페이지 진위 검증 모드
- JPG, PNG, PDF 업로드
- PDF 전체 페이지 미리보기 및 분석
- ELA, 국소 노이즈 불일치, 블러 차이, 배경 질감 불일치 분석
- 최대 5개의 빨간 추가 검토 후보 박스 표시
- 샘플용 문서 AI생성 버튼으로 매번 다른 발표용 문서 생성 및 즉시 진위 검토
- 웹페이지 캡처 이미지 분석
- URL 접속 가능 여부, 리다이렉트, 도메인, HTTPS, 페이지 제목 점검
- 의심 키워드 탐지
- 웹 증거 신뢰도 점수 및 위험도 리포트

## 파일 구조

```text
app.py
forensics.py
web_forensics.py
sample_generator.py
requirements.txt
README.md
```

## 설치 방법

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

## 실행 방법

```bash
streamlit run app.py
```

Streamlit 실행 파일이 PATH에 없다면 다음 명령을 사용하세요.

```bash
python -m streamlit run app.py
```

## 참고

URL 검증은 API 키 없이 `requests`와 `BeautifulSoup`으로 동작합니다. URL 접속에 실패해도 앱이 멈추지 않고 실패 사유를 리포트에 표시합니다.

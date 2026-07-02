# DocuGuard AI

DocuGuard AI는 계약서, 공문, 보험 문서의 위조 탐지를 목표로 하는 Streamlit 기반 웹 MVP입니다.

현재 버전은 OpenCV 기반 분석을 연결한 MVP입니다. 업로드된 문서 이미지 또는 PDF 첫 페이지를 대상으로 ELA, 노이즈 불일치, 블러 차이 분석을 실행합니다.

## 현재 구현 범위

- JPG, PNG, PDF 파일 업로드
- PDF 첫 페이지 이미지 변환
- 원본 문서 미리보기
- 분석 시작 버튼
- ELA 기반 압축 흔적 분석
- 노이즈 불일치 분석
- 선명도/블러 차이 분석
- 위조 의심 점수 표시
- 의심 영역 빨간 박스 표시
- 낮음 / 주의 / 높음 판정 표시
- 해커톤 발표용 정상/조작 계약서 샘플 생성
- 조작 샘플 생성 후 즉시 분석
- 분석 의심 사유 문장 표시

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

## 다음 단계

다음 단계에서는 텍스트 주변 압축 흔적, 서명/도장 색상 이상 탐지, 점수 보정 로직을 더 정교하게 개선할 수 있습니다.

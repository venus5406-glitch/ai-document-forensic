# DocuGuard AI

DocuGuard AI는 계약서, 공문, 보험 문서의 위조 탐지를 목표로 하는 Streamlit 기반 웹 MVP입니다.

현재 버전은 1단계 MVP입니다. 복잡한 이미지 포렌식 분석은 아직 연결하지 않고, 전체 화면 흐름이 깨지지 않는지 확인하는 데 집중합니다.

## 현재 구현 범위

- JPG, PNG, PDF 파일 업로드
- PDF 첫 페이지 이미지 변환
- 원본 문서 미리보기
- 분석 시작 버튼
- 더미 위조 의심 점수 표시
- 낮음 / 주의 판정 표시

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

2단계에서는 ELA, 노이즈 불일치, 블러 차이, 텍스트 주변 압축 흔적, 서명/도장 색상 이상 탐지 로직을 순차적으로 연결할 수 있습니다.

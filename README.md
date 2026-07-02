# DocuGuard AI

AI로 문서 위조 흔적을 탐지하는 Streamlit 기반 해커톤 MVP입니다. 계약서, 공문, 보험 문서 이미지 또는 PDF를 업로드하면 OpenCV 기반 포렌식 분석으로 위조 의심 점수와 의심 영역 표시 이미지를 제공합니다.

## 주요 기능

- JPG, PNG, PDF 업로드
- PDF 첫 페이지 이미지 변환
- 원본 문서 미리보기
- Error Level Analysis(ELA)
- 노이즈 불일치 분석
- 선명도/블러 차이 분석
- 텍스트 영역 주변 압축 흔적 분석
- 서명/도장 영역 색상 이상 감지
- 위조 의심 점수 0~100점 출력
- 의심 영역 빨간 박스 시각화
- 최종 판정: 낮음 / 주의 / 높음
- 해커톤 데모용 정상/조작 문서 샘플 생성 및 다운로드

## 파일 구조

```text
app.py
forensics.py
sample_generator.py
requirements.txt
README.md
```

## 설치 방법

Python 3.11 이상을 권장합니다.

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

브라우저에서 Streamlit이 안내하는 로컬 주소를 열면 `DocuGuard AI` 화면을 볼 수 있습니다.

## 분석 방식

이 MVP는 GPT API 호출 없이 이미지 포렌식 로직을 직접 수행합니다.

- ELA: JPEG 재압축 전후 차이를 통해 편집 흔적 후보를 찾습니다.
- 노이즈 분석: wavelet denoise 잔차를 이용해 주변과 다른 노이즈 패턴을 찾습니다.
- 블러 분석: Laplacian 기반 선명도 편차로 붙여넣기 또는 재편집 후보를 찾습니다.
- 압축 흔적 분석: 텍스트 경계와 JPEG 블록 단위 흔적을 함께 확인합니다.
- 색상 이상 분석: 도장, 서명, 컬러 잉크 후보 영역의 색상 분포 이상을 찾습니다.

## 주의사항

DocuGuard AI는 해커톤 MVP 및 1차 스크리닝 도구입니다. 법적 효력이 필요한 문서 감정에는 원본 파일, 메타데이터, 스캐너 이력, 전문 감정 절차가 필요합니다.

from __future__ import annotations

import streamlit as st

from forensics import analyze_document, load_document_preview
from sample_generator import create_contract_sample


st.set_page_config(
    page_title="DocuGuard AI",
    page_icon="DG",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    _apply_style()
    _render_sidebar()
    _render_header()

    document_image = _select_document()
    if document_image is None:
        _render_empty_state()
        return

    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        st.markdown("### 원본 문서 보기")
        st.image(document_image, caption=st.session_state["document_name"], use_container_width=True)

    with right:
        st.markdown("### 분석")
        st.write("ELA, 노이즈 불일치, 블러 차이 분석으로 문서의 조작 의심 영역을 찾습니다.")

        if st.button("분석 시작", type="primary", use_container_width=True):
            _run_analysis(document_image)

        result = st.session_state.get("analysis_result")
        if result:
            _render_analysis_result(result)
        else:
            st.info("분석 시작 버튼을 누르면 위조 의심 점수와 표시 이미지를 확인할 수 있습니다.")


def _select_document():
    sample_left, sample_right = st.columns(2)
    with sample_left:
        if st.button("정상 계약서 샘플 생성", use_container_width=True):
            _set_document(create_contract_sample(tampered=False), "정상 계약서 샘플")
    with sample_right:
        if st.button("조작 계약서 샘플 생성", use_container_width=True):
            image = create_contract_sample(tampered=True)
            _set_document(image, "날짜/금액/서명 조작 계약서 샘플")
            _run_analysis(image)

    uploaded_file = st.file_uploader(
        "문서 파일 업로드",
        type=["jpg", "jpeg", "png", "pdf"],
        help="JPG, PNG, PDF를 지원합니다. PDF는 첫 페이지만 분석합니다.",
    )

    if uploaded_file is not None:
        try:
            image = load_document_preview(uploaded_file)
        except Exception as exc:
            st.error(f"파일을 불러오지 못했습니다: {exc}")
            return st.session_state.get("document_image")

        if st.session_state.get("document_name") != uploaded_file.name:
            _set_document(image, uploaded_file.name)

    return st.session_state.get("document_image")


def _set_document(image, name: str) -> None:
    st.session_state["document_image"] = image
    st.session_state["document_name"] = name
    st.session_state.pop("analysis_result", None)


def _run_analysis(image) -> None:
    with st.spinner("문서 위조 의심 영역을 분석하는 중입니다..."):
        st.session_state["analysis_result"] = analyze_document(image)


def _render_header() -> None:
    st.markdown(
        """
        <section class="hero">
          <div>
            <p class="eyebrow">Document Forgery Detection MVP</p>
            <h1>DocuGuard AI</h1>
            <p class="subtitle">AI로 문서 위조 흔적을 탐지합니다</p>
          </div>
          <div class="stage-badge">Hackathon Demo</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## DocuGuard AI")
        st.caption("계약서, 공문, 보험 문서 위조 탐지 MVP")
        st.divider()
        st.markdown("### 데모 기능")
        st.markdown(
            """
            - 정상 계약서 샘플 생성
            - 날짜/금액/서명 조작 샘플 생성
            - 샘플 즉시 분석
            - 의심 영역 빨간 박스 표시
            """
        )
        st.divider()
        st.markdown("### 분석 항목")
        st.markdown(
            """
            - Error Level Analysis(ELA)
            - 노이즈 불일치 분석
            - 선명도/블러 차이 분석
            """
        )
        st.info("이 MVP는 1차 스크리닝 도구입니다. 법적 감정에는 원본 파일과 전문 감정 절차가 필요합니다.")


def _render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
          <h3>문서를 업로드하거나 샘플을 생성하세요</h3>
          <p>발표 데모에서는 조작 계약서 샘플 생성 버튼을 누르면 바로 분석 결과까지 확인할 수 있습니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_analysis_result(result: dict) -> None:
    score = int(result["score"])
    level = str(result["level"])
    level_class = "low" if score < 40 else "warn" if score < 70 else "high"

    st.markdown(
        f"""
        <div class="result-panel">
          <span class="panel-label">위조 의심 점수</span>
          <strong class="{level_class}">{score}/100</strong>
          <p>최종 판정: <b>{level}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(score / 100)
    st.markdown("#### 의심 영역 표시 이미지")
    st.image(result["result_image"], caption="빨간 박스: 위조 의심 영역", use_container_width=True)
    st.markdown("#### 분석 리포트")
    st.write(result["summary"])
    for reason in result["reasons"]:
        st.markdown(f"- {reason}")


def _apply_style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f5f7fb;
            color: #0f172a;
        }
        .hero {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            padding: 30px 34px;
            margin-bottom: 24px;
            background: linear-gradient(135deg, #102033 0%, #144153 52%, #1f6f6a 100%);
            color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.16);
        }
        .hero h1 {
            margin: 0;
            font-size: 44px;
            line-height: 1.05;
            letter-spacing: 0;
        }
        .eyebrow {
            margin: 0 0 8px;
            color: #bae6fd;
            font-size: 13px;
            text-transform: uppercase;
        }
        .subtitle {
            margin: 10px 0 0;
            color: #e0f2fe;
            font-size: 19px;
        }
        .stage-badge {
            padding: 10px 14px;
            border: 1px solid rgba(255,255,255,0.35);
            border-radius: 6px;
            color: #ecfeff;
            white-space: nowrap;
        }
        .empty-state {
            padding: 34px;
            background: #ffffff;
            border: 1px dashed #94a3b8;
            border-radius: 8px;
            text-align: center;
        }
        .empty-state h3 {
            margin-top: 0;
        }
        .result-panel {
            padding: 22px;
            margin-top: 18px;
            background: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }
        .panel-label {
            display: block;
            color: #64748b;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .result-panel strong {
            display: block;
            font-size: 42px;
            line-height: 1.1;
            margin-bottom: 8px;
        }
        .result-panel strong.low { color: #16a34a; }
        .result-panel strong.warn { color: #f59e0b; }
        .result-panel strong.high { color: #dc2626; }
        @media (max-width: 800px) {
            .hero {
                display: grid;
                grid-template-columns: 1fr;
            }
            .hero h1 {
                font-size: 34px;
            }
            .stage-badge {
                white-space: normal;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

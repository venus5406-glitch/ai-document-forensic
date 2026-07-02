from __future__ import annotations

import streamlit as st

from forensics import analyze_document_dummy, load_document_preview


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

    uploaded_file = st.file_uploader(
        "문서 파일 업로드",
        type=["jpg", "jpeg", "png", "pdf"],
        help="JPG, PNG, PDF를 지원합니다. PDF는 첫 페이지만 미리보기로 변환합니다.",
    )

    if uploaded_file is None:
        _render_empty_state()
        return

    try:
        document_image = load_document_preview(uploaded_file)
    except Exception as exc:
        st.error(f"파일을 불러오지 못했습니다: {exc}")
        return

    st.session_state["document_name"] = uploaded_file.name
    st.session_state["document_image"] = document_image

    left, right = st.columns([1.15, 0.85], gap="large")

    with left:
        st.markdown("### 원본 문서 보기")
        st.image(document_image, caption=uploaded_file.name, use_container_width=True)

    with right:
        st.markdown("### 분석 준비")
        st.write("업로드된 문서가 정상적으로 로드되었습니다. 아래 버튼을 눌러 1단계 더미 분석을 실행하세요.")

        analyze_clicked = st.button(
            "분석 시작",
            type="primary",
            use_container_width=True,
        )

        if analyze_clicked:
            with st.spinner("문서 화면 흐름을 검증하는 중입니다..."):
                st.session_state["analysis_result"] = analyze_document_dummy(uploaded_file.name)

        result = st.session_state.get("analysis_result")
        if result:
            _render_dummy_result(result)
        else:
            st.info("아직 분석 결과가 없습니다. 분석 시작 버튼을 눌러 더미 점수를 확인하세요.")


def _render_header() -> None:
    st.markdown(
        """
        <section class="hero">
          <div>
            <p class="eyebrow">Document Forgery Detection MVP</p>
            <h1>DocuGuard AI</h1>
            <p class="subtitle">AI로 문서 위조 흔적을 탐지합니다</p>
          </div>
          <div class="stage-badge">1단계 MVP</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## DocuGuard AI")
        st.caption("계약서, 공문, 보험 문서 위조 탐지 MVP")
        st.divider()
        st.markdown("### 현재 구현 범위")
        st.markdown(
            """
            - 파일 업로드
            - 이미지/PDF 첫 페이지 미리보기
            - 분석 버튼
            - 더미 위조 점수 표시
            """
        )
        st.info("이번 단계에서는 복잡한 포렌식 분석 로직을 실행하지 않습니다.")


def _render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
          <h3>문서를 업로드하세요</h3>
          <p>JPG, PNG 또는 PDF 파일을 올리면 원본 미리보기와 분석 버튼이 표시됩니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_dummy_result(result: dict[str, str | int]) -> None:
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
    st.markdown("#### 분석 리포트")
    st.write(result["message"])
    st.caption("이 점수는 화면 흐름 검증을 위한 더미 값입니다. 실제 탐지 로직은 다음 단계에서 연결합니다.")


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

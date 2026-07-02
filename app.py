from __future__ import annotations

from io import BytesIO

import matplotlib.pyplot as plt
import streamlit as st

from forensics import load_document, run_forensic_analysis
from sample_generator import create_sample_document, sample_png_bytes


st.set_page_config(
    page_title="DocuGuard AI",
    page_icon="DG",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    _style()
    _sidebar()

    st.markdown(
        """
        <section class="hero">
          <div>
            <p class="eyebrow">AI Document Forensic MVP</p>
            <h1>DocuGuard AI</h1>
            <p class="subtitle">AI로 문서 위조 흔적을 탐지합니다</p>
          </div>
          <div class="hero-badge">OpenCV 기반 분석</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "문서 이미지 또는 PDF 업로드",
        type=["jpg", "jpeg", "png", "pdf"],
        help="PDF는 첫 페이지만 분석합니다.",
    )

    sample_choice = st.segmented_control(
        "해커톤 데모 샘플",
        options=["업로드 사용", "정상 문서 샘플", "조작 문서 샘플"],
        default="업로드 사용",
    )

    image = None
    source_label = ""

    if sample_choice != "업로드 사용":
        image = create_sample_document(tampered=sample_choice == "조작 문서 샘플")
        source_label = sample_choice
    elif uploaded is not None:
        try:
            image = load_document(uploaded)
            source_label = uploaded.name
        except Exception as exc:
            st.error(f"문서를 불러오지 못했습니다: {exc}")
            return

    if image is None:
        _empty_state()
        return

    with st.spinner("문서의 압축 흔적, 노이즈, 블러, 컬러 잉크 패턴을 분석하는 중입니다..."):
        analysis = run_forensic_analysis(image)

    _results(image, analysis, source_label)


def _sidebar() -> None:
    with st.sidebar:
        st.markdown("### DocuGuard AI")
        st.caption("계약서, 공문, 보험 문서의 부분 편집 흔적을 빠르게 스크리닝합니다.")
        st.download_button(
            "정상 샘플 다운로드",
            data=sample_png_bytes(tampered=False),
            file_name="docuguard_normal_sample.png",
            mime="image/png",
            use_container_width=True,
        )
        st.download_button(
            "조작 샘플 다운로드",
            data=sample_png_bytes(tampered=True),
            file_name="docuguard_tampered_sample.png",
            mime="image/png",
            use_container_width=True,
        )
        st.divider()
        st.markdown("#### 분석 엔진")
        st.write("ELA, 노이즈 잔차, Laplacian 선명도, JPEG 블록 흔적, 서명/도장 색상 이상을 조합합니다.")
        st.info("본 MVP는 포렌식 보조 도구입니다. 법적 최종 감정에는 원본 파일과 전문 감정 절차가 필요합니다.")


def _empty_state() -> None:
    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown("### 문서를 업로드하거나 샘플을 선택하세요")
        st.write("JPG, PNG, PDF 문서를 넣으면 첫 페이지를 분석하고 의심 영역을 빨간 박스로 표시합니다.")
    with right:
        st.image(create_sample_document(tampered=True), caption="데모용 조작 샘플 미리보기")


def _results(image, analysis: dict, source_label: str) -> None:
    score = analysis["score"]
    verdict = analysis["verdict"]
    score_class = "low" if score < 40 else "warn" if score < 70 else "high"

    st.markdown(
        f"""
        <div class="score-row">
          <div class="metric-card">
            <span>분석 문서</span>
            <strong>{source_label}</strong>
          </div>
          <div class="metric-card {score_class}">
            <span>위조 의심 점수</span>
            <strong>{score}/100</strong>
          </div>
          <div class="metric-card {score_class}">
            <span>최종 판정</span>
            <strong>{verdict}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_original, tab_analysis, tab_report = st.tabs(["원본 문서 보기", "분석 결과 보기", "분석 리포트"])

    with tab_original:
        st.image(image, caption="원본 문서", use_container_width=True)

    with tab_analysis:
        col1, col2 = st.columns(2)
        with col1:
            st.image(analysis["result_image"], caption="의심 영역 표시 이미지", use_container_width=True)
        with col2:
            st.image(analysis["heatmap"], caption="종합 의심 히트맵", use_container_width=True)
            st.image(analysis["ela_preview"], caption="ELA 반응 미리보기", use_container_width=True)

    with tab_report:
        st.markdown("### 분석 리포트")
        st.progress(score / 100)
        for finding in analysis["findings"]:
            st.markdown(
                f"""
                <div class="finding">
                  <div>
                    <strong>{finding.label}</strong>
                    <p>{finding.description}</p>
                  </div>
                  <span>{finding.severity:.1f}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### 판정 기준")
        chart = _score_chart(score)
        st.pyplot(chart, clear_figure=True)

        buffer = BytesIO()
        analysis["result_image"].save(buffer, format="PNG")
        st.download_button(
            "분석 결과 이미지 다운로드",
            data=buffer.getvalue(),
            file_name="docuguard_analysis_result.png",
            mime="image/png",
            use_container_width=True,
        )


def _score_chart(score: int):
    fig, ax = plt.subplots(figsize=(7, 1.2))
    ax.barh(["위조 의심"], [score], color="#dc2626" if score >= 70 else "#f59e0b" if score >= 40 else "#16a34a")
    ax.set_xlim(0, 100)
    ax.axvspan(0, 40, color="#dcfce7", alpha=0.7)
    ax.axvspan(40, 70, color="#fef3c7", alpha=0.7)
    ax.axvspan(70, 100, color="#fee2e2", alpha=0.7)
    ax.set_xlabel("Score")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    return fig


def _style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f5f7fb;
            color: #0f172a;
        }
        .hero {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 24px;
            padding: 30px 34px;
            margin-bottom: 22px;
            background: linear-gradient(135deg, #102033 0%, #144153 48%, #1f6f6a 100%);
            color: white;
            border-radius: 8px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.16);
        }
        .hero h1 {
            margin: 0;
            font-size: 44px;
            letter-spacing: 0;
        }
        .eyebrow {
            margin: 0 0 8px 0;
            font-size: 13px;
            text-transform: uppercase;
            color: #bae6fd;
        }
        .subtitle {
            margin: 8px 0 0 0;
            color: #e0f2fe;
            font-size: 19px;
        }
        .hero-badge {
            border: 1px solid rgba(255,255,255,0.35);
            padding: 10px 14px;
            border-radius: 6px;
            color: #ecfeff;
            white-space: nowrap;
        }
        .score-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin: 12px 0 22px 0;
        }
        .metric-card {
            background: white;
            border: 1px solid #dbe3ef;
            border-left: 5px solid #2563eb;
            border-radius: 8px;
            padding: 16px 18px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }
        .metric-card span {
            display: block;
            color: #64748b;
            font-size: 13px;
            margin-bottom: 7px;
        }
        .metric-card strong {
            display: block;
            font-size: 25px;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }
        .metric-card.low { border-left-color: #16a34a; }
        .metric-card.warn { border-left-color: #f59e0b; }
        .metric-card.high { border-left-color: #dc2626; }
        .finding {
            display: flex;
            justify-content: space-between;
            gap: 18px;
            align-items: center;
            padding: 16px 18px;
            margin: 10px 0;
            background: #ffffff;
            border: 1px solid #dbe3ef;
            border-radius: 8px;
        }
        .finding p {
            margin: 6px 0 0 0;
            color: #475569;
        }
        .finding span {
            min-width: 64px;
            text-align: center;
            background: #fee2e2;
            color: #991b1b;
            border-radius: 6px;
            padding: 8px 10px;
            font-weight: 700;
        }
        @media (max-width: 800px) {
            .hero, .score-row {
                grid-template-columns: 1fr;
                display: grid;
            }
            .hero h1 {
                font-size: 34px;
            }
            .hero-badge {
                white-space: normal;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

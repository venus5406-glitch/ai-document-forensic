from __future__ import annotations

import streamlit as st

from forensics import analyze_document, load_document_pages
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

    pages = _select_document()
    if not pages:
        _render_empty_state()
        return

    page_count = len(pages)
    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        st.markdown("### Original Document")
        st.caption(f"{st.session_state['document_name']} · {page_count} page(s)")
        selected_page = st.selectbox(
            "Preview page",
            options=list(range(1, page_count + 1)),
            format_func=lambda page: f"Page {page}",
        )
        st.image(pages[selected_page - 1], caption=f"Page {selected_page}", use_container_width=True)

        with st.expander("Preview all pages"):
            for index, page in enumerate(pages, start=1):
                st.image(page, caption=f"Page {index}", use_container_width=True)

    with right:
        st.markdown("### Analysis")
        st.write("PDF uploads are loaded page by page. The analysis focuses on local pattern differences, not all text edges.")

        if st.button("Analyze all pages", type="primary", use_container_width=True):
            _run_analysis(pages)

        results = st.session_state.get("analysis_results")
        if results:
            _render_analysis_results(results)
        else:
            st.info("Run analysis to see review-candidate regions and per-page scores.")


def _select_document() -> list:
    sample_left, sample_right = st.columns(2)
    with sample_left:
        if st.button("Generate normal contract sample", use_container_width=True):
            _set_document([create_contract_sample(tampered=False)], "Normal contract sample")
    with sample_right:
        if st.button("Generate tampered contract sample", use_container_width=True):
            pages = [create_contract_sample(tampered=True)]
            _set_document(pages, "Tampered date/amount/signature sample")
            _run_analysis(pages)

    uploaded_file = st.file_uploader(
        "Upload document",
        type=["jpg", "jpeg", "png", "pdf"],
        help="JPG, PNG, and PDF are supported. PDF files are analyzed across all pages.",
    )

    if uploaded_file is not None:
        try:
            pages = load_document_pages(uploaded_file)
        except Exception as exc:
            st.error(f"Could not load file: {exc}")
            return st.session_state.get("document_pages", [])

        current_key = f"{uploaded_file.name}:{uploaded_file.size}"
        if st.session_state.get("document_key") != current_key:
            _set_document(pages, uploaded_file.name, current_key)

    return st.session_state.get("document_pages", [])


def _set_document(pages: list, name: str, key: str | None = None) -> None:
    st.session_state["document_pages"] = pages
    st.session_state["document_name"] = name
    st.session_state["document_key"] = key or name
    st.session_state.pop("analysis_results", None)


def _run_analysis(pages: list) -> None:
    progress = st.progress(0)
    results = []

    with st.spinner("Analyzing all pages for local review candidates..."):
        total = len(pages)
        for index, page in enumerate(pages, start=1):
            result = analyze_document(page)
            result["page"] = index
            results.append(result)
            progress.progress(index / total)

    st.session_state["analysis_results"] = results


def _render_header() -> None:
    st.markdown(
        """
        <section class="hero">
          <div>
            <p class="eyebrow">Document Forgery Detection MVP</p>
            <h1>DocuGuard AI</h1>
            <p class="subtitle">Detect document tampering traces with image forensics</p>
          </div>
          <div class="stage-badge">All Pages PDF</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## DocuGuard AI")
        st.caption("Contract, notice, and insurance document screening MVP")
        st.divider()
        st.markdown("### Demo")
        st.markdown(
            """
            - Generate normal contract sample
            - Generate tampered sample
            - Preview every PDF page
            - Analyze every PDF page
            - Show up to 5 review-candidate boxes
            """
        )
        st.divider()
        st.markdown("### Checks")
        st.markdown(
            """
            - Error Level Analysis
            - Local noise mismatch
            - Sharpness / blur mismatch
            """
        )
        st.info("This MVP finds additional review candidates. It does not make a final authenticity decision.")


def _render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
          <h3>Upload a document or generate a sample</h3>
          <p>For PDFs, all pages are loaded and can be analyzed together.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_analysis_results(results: list[dict]) -> None:
    max_score = max(int(result["score"]) for result in results)
    high_page = max(results, key=lambda result: int(result["score"]))
    level_class = "low" if max_score < 40 else "warn" if max_score < 70 else "high"

    st.markdown(
        f"""
        <div class="result-panel">
          <span class="panel-label">Highest review-candidate score</span>
          <strong class="{level_class}">{max_score}/100</strong>
          <p>Highest page: <b>Page {high_page["page"]}</b> · Level: <b>{high_page["level"]}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(max_score / 100)

    page_labels = [f"Page {result['page']} · {result['score']}/100" for result in results]
    tabs = st.tabs(page_labels)

    for tab, result in zip(tabs, results):
        with tab:
            st.markdown(f"#### Page {result['page']} result")
            st.image(result["result_image"], caption="Red boxes: additional review candidates", use_container_width=True)
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

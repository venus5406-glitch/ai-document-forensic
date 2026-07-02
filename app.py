from __future__ import annotations

from io import BytesIO

from PIL import Image
import streamlit as st

from forensics import analyze_document, load_document_pages
from sample_generator import create_contract_sample
from web_forensics import analyze_url


DOCUMENT_MODE = "문서 위조 탐지"
WEB_MODE = "웹페이지 진위 검증"


st.set_page_config(
    page_title="DocuGuard AI",
    page_icon="DG",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    _apply_style()
    mode = _render_sidebar()
    _render_header(mode)

    if mode == DOCUMENT_MODE:
        _document_mode()
    else:
        _web_mode()


def _document_mode() -> None:
    pages = _select_document()
    if not pages:
        _render_empty_state(
            "문서를 업로드하거나 샘플용 문서 AI생성을 실행하세요",
            "샘플용 문서 AI생성은 매번 다른 발표용 문서를 만들고 진위 검토 결과까지 바로 보여줍니다.",
        )
        return

    page_count = len(pages)
    left, right = st.columns([1.1, 0.9], gap="large")

    with left:
        st.markdown("### 원본 문서 보기")
        st.caption(f"{st.session_state['document_name']} · 총 {page_count}페이지")
        selected_page = st.selectbox(
            "미리보기 페이지",
            options=list(range(1, page_count + 1)),
            format_func=lambda page: f"{page}페이지",
        )
        st.image(pages[selected_page - 1], caption=f"{selected_page}페이지", use_container_width=True)

        with st.expander("전체 페이지 미리보기"):
            for index, page in enumerate(pages, start=1):
                st.image(page, caption=f"{index}페이지", use_container_width=True)

    with right:
        st.markdown("### 분석")
        st.write("일반 텍스트 전체가 아니라 국소적으로 다른 패턴을 추가 검토 후보로 찾습니다.")

        if st.button("전체 페이지 분석 시작", type="primary", use_container_width=True):
            _run_document_analysis(pages)

        results = st.session_state.get("analysis_results")
        if results:
            _render_document_results(results)
        else:
            st.info("분석을 실행하면 페이지별 점수와 추가 검토 후보 영역을 확인할 수 있습니다.")


def _web_mode() -> None:
    st.markdown("### 웹페이지 진위 검증")
    st.write("웹페이지 캡처 이미지 또는 URL을 분석합니다. 최종 판정이 아니라 추가 검토 후보를 선별합니다.")

    image_col, url_col = st.columns(2, gap="large")

    with image_col:
        st.markdown("#### 캡처 이미지")
        uploaded = st.file_uploader(
            "웹페이지 캡처 이미지 업로드",
            type=["jpg", "jpeg", "png"],
            help="캡처 이미지는 ELA, 노이즈 불일치, 블러 차이 기준으로 분석합니다.",
            key="web_capture_upload",
        )
        if uploaded is not None:
            try:
                image = Image.open(BytesIO(uploaded.getvalue())).convert("RGB")
                st.session_state["web_capture_image"] = image
                st.image(image, caption=uploaded.name, use_container_width=True)
            except Exception as exc:
                st.error(f"캡처 이미지를 불러오지 못했습니다: {exc}")

        if st.button("캡처 이미지 분석", type="primary", use_container_width=True):
            image = st.session_state.get("web_capture_image")
            if image is None:
                st.warning("먼저 웹페이지 캡처 이미지를 업로드하세요.")
            else:
                with st.spinner("캡처 이미지의 부분 편집 후보를 분석하는 중입니다..."):
                    st.session_state["web_capture_result"] = analyze_document(image)

    with url_col:
        st.markdown("#### URL")
        url = st.text_input("웹페이지 URL 입력", placeholder="https://example.com/event")
        if st.button("URL 분석", type="primary", use_container_width=True):
            if not url.strip():
                st.warning("먼저 URL을 입력하세요.")
            else:
                with st.spinner("접속 가능 여부, 리다이렉트, 도메인, 의심 키워드를 확인하는 중입니다..."):
                    st.session_state["web_url_result"] = analyze_url(url)

    capture_result = st.session_state.get("web_capture_result")
    url_result = st.session_state.get("web_url_result")

    if capture_result or url_result:
        st.divider()
        _render_web_results(capture_result, url_result)


def _select_document() -> list:
    st.markdown("### 샘플 데모")
    st.write("버튼을 누를 때마다 다른 샘플 문서를 생성하고, 즉시 진위 검토 결과까지 확인합니다.")
    if st.button("샘플용 문서 AI생성", type="primary", use_container_width=True):
        pages = [create_contract_sample(tampered=True)]
        _set_document(pages, "샘플용 문서 AI생성")
        _run_document_analysis(pages)

    uploaded_file = st.file_uploader(
        "문서 파일 업로드",
        type=["jpg", "jpeg", "png", "pdf"],
        help="JPG, PNG, PDF를 지원합니다. PDF는 모든 페이지를 분석합니다.",
    )

    if uploaded_file is not None:
        try:
            pages = load_document_pages(uploaded_file)
        except Exception as exc:
            st.error(f"파일을 불러오지 못했습니다: {exc}")
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


def _run_document_analysis(pages: list) -> None:
    progress = st.progress(0)
    results = []

    with st.spinner("모든 페이지의 추가 검토 후보를 분석하는 중입니다..."):
        total = len(pages)
        for index, page in enumerate(pages, start=1):
            result = analyze_document(page)
            result["page"] = index
            results.append(result)
            progress.progress(index / total)

    st.session_state["analysis_results"] = results


def _render_header(mode: str) -> None:
    badge = "문서 포렌식" if mode == DOCUMENT_MODE else "웹 증거 검토"
    subtitle = (
        "AI로 문서 위조 흔적을 탐지합니다"
        if mode == DOCUMENT_MODE
        else "웹페이지 캡처와 URL의 조작 또는 피싱 가능성을 검토합니다"
    )
    st.markdown(
        f"""
        <section class="hero">
          <div>
            <p class="eyebrow">DocuGuard AI MVP</p>
            <h1>DocuGuard AI</h1>
            <p class="subtitle">{subtitle}</p>
          </div>
          <div class="stage-badge">{badge}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> str:
    with st.sidebar:
        st.markdown("## DocuGuard AI")
        st.caption("문서와 웹페이지 증거를 검토하는 해커톤 MVP")
        mode = st.radio("분석 모드 선택", [DOCUMENT_MODE, WEB_MODE], horizontal=False)
        st.divider()

        if mode == DOCUMENT_MODE:
            st.markdown("### 문서 분석 항목")
            st.markdown(
                """
                - ELA 압축 흔적 분석
                - 국소 노이즈 불일치
                - 선명도/블러 차이
                - PDF 전체 페이지 분석
                """
            )
        else:
            st.markdown("### 웹 분석 항목")
            st.markdown(
                """
                - 캡처 이미지 편집 후보
                - URL 접속 가능 여부
                - 도메인 패턴 검토
                - 리다이렉트 경고
                - 의심 키워드 탐지
                """
            )

        st.info("이 MVP는 추가 검토 후보를 선별합니다. 법적 또는 최종 진위 판단이 아닙니다.")
        return mode


def _render_empty_state(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
          <h3>{title}</h3>
          <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_document_results(results: list[dict]) -> None:
    max_score = max(int(result["score"]) for result in results)
    high_page = max(results, key=lambda result: int(result["score"]))
    level_class = "low" if max_score < 40 else "warn" if max_score < 70 else "high"

    st.markdown(
        f"""
        <div class="result-panel">
          <span class="panel-label">최고 추가 검토 점수</span>
          <strong class="{level_class}">{max_score}/100</strong>
          <p>최고 의심 페이지: <b>{high_page["page"]}페이지</b> · 위험도: <b>{_translate_level(high_page["level"])}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(max_score / 100)

    page_labels = [f"{result['page']}페이지 · {result['score']}/100" for result in results]
    tabs = st.tabs(page_labels)

    for tab, result in zip(tabs, results):
        with tab:
            st.markdown(f"#### {result['page']}페이지 분석 결과")
            st.image(result["result_image"], caption="빨간 박스: 추가 검토 후보", use_container_width=True)
            st.write(_translate_text(result["summary"]))
            for reason in result["reasons"]:
                st.markdown(f"- {_translate_text(reason)}")


def _render_web_results(capture_result: dict | None, url_result: dict | None) -> None:
    capture_score = int(capture_result["score"]) if capture_result else 100
    url_score = int(url_result["trust_score"]) if url_result else 100
    trust_score = min(capture_score, url_score)
    risk_level = _web_risk_level(trust_score)
    level_class = "low" if trust_score >= 75 else "warn" if trust_score >= 45 else "high"

    st.markdown(
        f"""
        <div class="result-panel">
          <span class="panel-label">웹 증거 신뢰도 점수</span>
          <strong class="{level_class}">{trust_score}/100</strong>
          <p>위험도: <b>{risk_level}</b></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(trust_score / 100)

    if capture_result:
        st.markdown("#### 캡처 이미지 검토")
        st.image(capture_result["result_image"], caption="빨간 박스: 캡처 이미지 추가 검토 후보", use_container_width=True)
        st.write(_translate_text(capture_result["summary"]))
        for reason in capture_result["reasons"]:
            st.markdown(f"- {_translate_text(reason)}")

    if url_result:
        st.markdown("#### URL 위험 요소 리포트")
        st.write(f"접속 가능 여부: `{url_result['reachable']}`")
        st.write(f"상태 코드: `{url_result['status_code']}`")
        st.write(f"프로토콜: `{url_result['scheme']}`")
        st.write(f"도메인: `{url_result['domain']}`")
        st.write(f"페이지 제목: `{url_result['title'] or '(제목 없음)'}`")
        st.write(f"최종 접속 URL: `{url_result['final_url']}`")

        redirect = url_result["redirect"]
        if redirect.get("redirected"):
            st.warning(redirect.get("warning") or "입력 URL과 최종 접속 URL이 다릅니다.")
        if url_result.get("error"):
            st.warning(url_result["error"])

        st.markdown("##### 의심 사유")
        for reason in url_result["reasons"]:
            st.markdown(f"- {reason}")


def _translate_level(level: str) -> str:
    return {"High": "높음", "Review": "주의", "Low": "낮음"}.get(level, level)


def _translate_text(text: str) -> str:
    translations = {
        "No strong local review candidates were found. This is not a final authenticity decision.": "강한 국소 추가 검토 후보는 발견되지 않았습니다. 최종 진위 판단은 아닙니다.",
        "No strong local anomalies were found after filtering ordinary text edges. This is an additional-review aid, not a final authenticity decision.": "일반 텍스트 엣지를 제외한 뒤 강한 국소 이상 신호는 낮게 관찰됩니다. 최종 판단이 아니라 추가 검토 보조 결과입니다.",
        "Some local areas react differently after JPEG recompression, so compression history mismatch is a review candidate.": "일부 영역에서 JPEG 재압축 반응이 달라 압축 이력 불일치가 추가 검토 후보입니다.",
        "A local noise pattern differs from the document-wide background pattern.": "국소 노이즈 패턴이 문서 전체 배경 패턴과 다릅니다.",
        "A local sharpness or blur pattern differs from nearby content.": "국소 선명도 또는 블러 패턴이 주변 내용과 다릅니다.",
        "Only the strongest merged local candidates are shown; ordinary text stroke edges are downweighted.": "일반 텍스트 획은 낮은 가중치로 처리하고, 병합된 상위 후보만 표시합니다.",
        "ELA, noise, and blur checks did not find strong local anomalies. This is not a final authenticity decision.": "ELA, 노이즈, 블러 검사에서 강한 국소 이상은 낮게 관찰됩니다. 최종 진위 판단은 아닙니다.",
    }
    if text in translations:
        return translations[text]
    if "local review candidate area(s)" in text:
        count = text.split(" local review", 1)[0]
        return f"{count}개의 국소 추가 검토 후보가 발견되었습니다. 일반 텍스트 엣지는 필터링했습니다."
    return text


def _web_risk_level(trust_score: int) -> str:
    if trust_score < 45:
        return "높음"
    if trust_score < 75:
        return "주의"
    return "낮음"


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

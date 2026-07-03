from __future__ import annotations

import json
import html

import streamlit as st
import streamlit.components.v1 as components

from document_vault import (
    MAX_VAULT_ITEMS,
    VAULT_STORAGE_KEY,
    add_document_to_vault,
    create_document_vault_item,
    filter_vault_items,
    local_storage_payload,
    remove_document_from_vault,
    sort_vault_items,
    utc_now_iso,
)
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
    if st.query_params.get("view") != "mvp":
        _render_landing_page()
        return

    sidebar_mode = st.query_params.get("sidebar")
    if "mvp_sidebar_pinned" not in st.session_state or sidebar_mode in {"pinned", "auto"}:
        st.session_state["mvp_sidebar_pinned"] = sidebar_mode != "auto"

    _show_mvp_sidebar(st.session_state["mvp_sidebar_pinned"])
    mode = _render_sidebar()
    _render_mvp_navbar()
    _render_header(mode)

    if mode == DOCUMENT_MODE:
        _document_mode()
    else:
        _web_mode()


def _render_landing_page() -> None:
    landing_markup = """
        <style>
        body:has(.landing-shell) [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1280px;
            padding-top: 2.2rem;
        }
        </style>
        <main class="landing-shell">
          <section class="landing-hero reveal">
            <div class="hero-copy">
              <h1>DocuGuard AI</h1>
              <h2>AI 기반 문서·웹페이지 진위 검증 플랫폼</h2>
              <p>
                AI가 문서와 웹페이지를 분석하여<br>
                위조 흔적과 신뢰도를 빠르게 검증합니다.
              </p>
            </div>
            <div class="hero-visual" aria-hidden="true">
              <div class="visual-grid"></div>
              <div class="scan-card card-a">
                <span>Document Trust</span>
                <strong>98.4%</strong>
                <i></i>
              </div>
              <div class="scan-card card-b">
                <span>Forgery Signal</span>
                <strong>AI Review</strong>
                <i></i>
              </div>
              <svg class="network-map" viewBox="0 0 520 360" role="img" aria-label="">
                <defs>
                  <linearGradient id="lineFlow" x1="0" x2="1" y1="0" y2="1">
                    <stop offset="0%" stop-color="#38BDF8" stop-opacity=".18"/>
                    <stop offset="50%" stop-color="#60A5FA" stop-opacity=".78"/>
                    <stop offset="100%" stop-color="#06B6D4" stop-opacity=".22"/>
                  </linearGradient>
                </defs>
                <path d="M70 250 C140 110, 240 310, 315 140 S445 125, 470 58" />
                <path d="M62 112 C165 82, 214 178, 292 205 S398 262, 474 210" />
                <path d="M118 305 C176 236, 188 134, 270 95 S395 68, 448 150" />
                <circle cx="70" cy="250" r="7" />
                <circle cx="315" cy="140" r="8" />
                <circle cx="470" cy="58" r="6" />
                <circle cx="292" cy="205" r="7" />
                <circle cx="118" cy="305" r="6" />
                <circle cx="270" cy="95" r="8" />
              </svg>
            </div>
            <a class="landing-cta-button hero-cta-button" href="?view=mvp" target="_self">
              <span>진위여부 판별하러 가기</span>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 12h14" />
                <path d="M13 6l6 6-6 6" />
              </svg>
            </a>
          </section>

          <section class="landing-section reveal">
            <div class="feature-grid">
              <article class="glass-feature">
                <div class="feature-icon">01</div>
                <h3>문서 위조 탐지</h3>
                <p>ELA 분석, 노이즈 분석, 압축 흔적 분석, PDF 분석을 통해 국소적인 위조 후보를 선별합니다.</p>
              </article>
              <article class="glass-feature">
                <div class="feature-icon">02</div>
                <h3>웹페이지 진위 검증</h3>
                <p>스크린샷 분석, 캡처 여부, 웹 위조, 피싱 가능성을 종합적으로 검토합니다.</p>
              </article>
              <article class="glass-feature">
                <div class="feature-icon">03</div>
                <h3>AI 포렌식 분석</h3>
                <p>AI 기반 분석, 시각적 결과, 신뢰도, 자동 리포트로 빠른 의사결정을 지원합니다.</p>
              </article>
            </div>
          </section>

          <section class="landing-section reveal">
            <div class="timeline">
              <div class="timeline-step">
                <svg class="flow-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M7 3h7l4 4v14H7z" />
                  <path d="M14 3v5h5" />
                  <path d="M9 13h6M9 17h4" />
                </svg>
                <b>01</b>
                <h3>문서 또는 URL 입력</h3>
              </div>
              <div class="timeline-step">
                <svg class="flow-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M8 8h8v8H8z" />
                  <path d="M4 10h4M4 14h4M16 10h4M16 14h4M10 4v4M14 4v4M10 16v4M14 16v4" />
                </svg>
                <b>02</b>
                <h3>AI 분석</h3>
              </div>
              <div class="timeline-step">
                <svg class="flow-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 4h14v16H5z" />
                  <path d="M8 9h8M8 13h5" />
                  <path d="M15 15l2 2 3-4" />
                </svg>
                <b>03</b>
                <h3>포렌식 결과 생성</h3>
              </div>
              <div class="timeline-step">
                <svg class="flow-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 3l8 4v5c0 5-3.4 8-8 9-4.6-1-8-4-8-9V7z" />
                  <path d="M8.5 12.5l2.2 2.2 4.8-5" />
                </svg>
                <b>04</b>
                <h3>진위 여부 확인</h3>
              </div>
            </div>
          </section>

          <section class="landing-section compare-section reveal">
            <div class="compare-grid">
              <article class="compare-card before">
                <span>기존 방식</span>
                <h3>느리고 주관적인 수동 검토</h3>
                <ul>
                  <li>육안 확인</li>
                  <li>시간 오래 걸림</li>
                  <li>전문가 필요</li>
                  <li>실수 가능</li>
                </ul>
              </article>
              <article class="compare-card after">
                <span>DocuGuard AI</span>
                <h3>빠르고 일관된 AI 기반 검증</h3>
                <ul>
                  <li>AI 자동 분석</li>
                  <li>수 초 내 분석</li>
                  <li>포렌식 기반</li>
                  <li>신뢰도 제공</li>
                </ul>
              </article>
            </div>
          </section>

        </main>
        """
    st.markdown(
        landing_markup,
        unsafe_allow_html=True,
    )


def _show_mvp_sidebar(is_pinned: bool) -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: block !important;
            visibility: visible !important;
            min-width: 21rem !important;
            width: 21rem !important;
            transform: translateX(0) !important;
            opacity: 1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _install_sidebar_reveal_controller(is_pinned)


def _render_mvp_navbar() -> None:
    st.markdown(
        """
        <nav class="mvp-navbar" aria-label="MVP navigation">
          <a href="/" target="_self">HOME</a>
          <span class="mvp-navbar-divider"></span>
          <strong>DocuGuard AI</strong>
        </nav>
        """,
        unsafe_allow_html=True,
    )


def _install_sidebar_reveal_controller(is_pinned: bool) -> None:
    components.html(
        f"""
        <script>
        (() => {{
          const doc = window.parent.document;
          const pinned = {json.dumps(is_pinned)};
          const styleId = "dg-sidebar-reveal-style";
          const edgeId = "dg-sidebar-reveal-edge";
          const indicatorId = "dg-sidebar-reveal-indicator";

          let style = doc.getElementById(styleId);
          if (!style) {{
            style = doc.createElement("style");
            style.id = styleId;
            doc.head.appendChild(style);
          }}
          style.textContent = `
            #${{edgeId}} {{
              position: fixed;
              inset: 0 auto 0 0;
              width: 18px;
              z-index: 999998;
              background: transparent;
              pointer-events: auto;
            }}
            #${{indicatorId}} {{
              position: fixed;
              left: 10px;
              top: 50%;
              z-index: 999999;
              display: grid;
              place-items: center;
              width: 28px;
              height: 48px;
              border: 1px solid rgba(148, 163, 184, 0.24);
              border-radius: 0 8px 8px 0;
              background: rgba(255, 255, 255, 0.62);
              color: #2563eb;
              box-shadow: 0 16px 34px rgba(37, 99, 235, 0.14);
              backdrop-filter: blur(14px);
              opacity: 0;
              transform: translate(-12px, -50%);
              transition: opacity 280ms ease-in-out, transform 280ms ease-in-out;
              font-size: 26px;
              font-weight: 800;
              line-height: 1;
              cursor: pointer;
              user-select: none;
            }}
            body.dg-sidebar-hidden #${{edgeId}}:hover + #${{indicatorId}},
            body.dg-sidebar-edge-hover #${{indicatorId}},
            body.dg-sidebar-open #${{indicatorId}} {{
              opacity: 1;
              transform: translate(0, -50%);
            }}
            body.dg-sidebar-reveal-enabled [data-testid="stSidebar"] {{
              transition: transform 320ms ease-in-out, opacity 320ms ease-in-out, box-shadow 320ms ease-in-out !important;
              will-change: transform, opacity;
              z-index: 999997 !important;
            }}
            body.dg-sidebar-reveal-enabled.dg-sidebar-hidden [data-testid="stSidebar"] {{
              transform: translateX(calc(-100% + 2px)) !important;
              opacity: 0.06 !important;
              pointer-events: none;
            }}
            body.dg-sidebar-reveal-enabled.dg-sidebar-open [data-testid="stSidebar"],
            body.dg-sidebar-reveal-enabled.dg-sidebar-pinned [data-testid="stSidebar"] {{
              transform: translateX(0) !important;
              opacity: 1 !important;
              pointer-events: auto;
              box-shadow: 18px 0 54px rgba(15, 23, 42, 0.12);
            }}
            body.dg-sidebar-pinned #${{edgeId}},
            body.dg-sidebar-pinned #${{indicatorId}} {{
              display: none;
            }}
            @media (hover: none), (max-width: 800px) {{
              #${{edgeId}} {{
                width: 44px;
              }}
              #${{indicatorId}} {{
                opacity: 1;
                transform: translate(0, -50%);
              }}
            }}
          `;

          let edge = doc.getElementById(edgeId);
          if (!edge) {{
            edge = doc.createElement("div");
            edge.id = edgeId;
            doc.body.appendChild(edge);
          }}

          let indicator = doc.getElementById(indicatorId);
          if (!indicator) {{
            indicator = doc.createElement("div");
            indicator.id = indicatorId;
            indicator.setAttribute("aria-label", "사이드바 펼치기");
            indicator.textContent = "›";
            doc.body.appendChild(indicator);
          }}

          const body = doc.body;
          body.classList.add("dg-sidebar-reveal-enabled");
          body.classList.toggle("dg-sidebar-pinned", pinned);
          body.classList.toggle("dg-sidebar-hidden", !pinned);
          body.classList.toggle("dg-sidebar-open", pinned);
          indicator.textContent = pinned ? "‹" : "›";

          let hideTimer = null;
          let interacting = false;

          const sidebar = () => doc.querySelector('[data-testid="stSidebar"]');
          const clearHide = () => {{
            if (hideTimer) window.clearTimeout(hideTimer);
            hideTimer = null;
          }};
          const openSidebar = () => {{
            if (pinned) return;
            clearHide();
            body.classList.remove("dg-sidebar-hidden");
            body.classList.add("dg-sidebar-open");
            indicator.textContent = "‹";
          }};
          const scheduleHide = () => {{
            if (pinned || interacting) return;
            clearHide();
            hideTimer = window.setTimeout(() => {{
              if (interacting) return;
              body.classList.add("dg-sidebar-hidden");
              body.classList.remove("dg-sidebar-open");
              indicator.textContent = "›";
            }}, 650);
          }};
          const markInteraction = () => {{
            interacting = true;
            window.setTimeout(() => {{
              interacting = false;
            }}, 900);
          }};

          edge.onmouseenter = () => {{
            body.classList.add("dg-sidebar-edge-hover");
            openSidebar();
          }};
          edge.onmouseleave = () => {{
            body.classList.remove("dg-sidebar-edge-hover");
            scheduleHide();
          }};
          indicator.onclick = () => {{
            if (body.classList.contains("dg-sidebar-open")) scheduleHide();
            else openSidebar();
          }};

          const bindSidebar = () => {{
            const side = sidebar();
            if (!side || side.dataset.dgRevealBound === "true") return;
            side.dataset.dgRevealBound = "true";
            side.addEventListener("mouseenter", openSidebar);
            side.addEventListener("mouseleave", scheduleHide);
            side.addEventListener("pointerdown", markInteraction, true);
            side.addEventListener("wheel", markInteraction, true);
            side.addEventListener("scroll", markInteraction, true);
          }};
          bindSidebar();
          window.setTimeout(bindSidebar, 300);
          window.setTimeout(bindSidebar, 900);
        }})();
        </script>
        """,
        height=0,
    )


def _document_mode() -> None:
    _render_vault_toolbar()

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
                image = load_document_pages(uploaded)[0]
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
        _set_document(pages, "샘플용 문서 AI생성", document_type="SAMPLE")
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
            _set_document(pages, uploaded_file.name, current_key, uploaded_file.type)

    return st.session_state.get("document_pages", [])


def _set_document(pages: list, name: str, key: str | None = None, document_type: str | None = None) -> None:
    st.session_state["document_pages"] = pages
    st.session_state["document_name"] = name
    st.session_state["document_key"] = key or name
    st.session_state["document_type"] = document_type or name.rsplit(".", 1)[-1].upper()
    st.session_state["document_uploaded_at"] = utc_now_iso()
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
    _save_current_document_to_vault(pages, results)


def _ensure_vault_state() -> None:
    st.session_state.setdefault("document_vault", [])
    st.session_state.setdefault("document_vault_open", False)


def _save_current_document_to_vault(pages: list, results: list[dict]) -> None:
    _ensure_vault_state()
    item = create_document_vault_item(
        name=st.session_state.get("document_name", "문서"),
        document_key=st.session_state.get("document_key", "document"),
        uploaded_at=st.session_state.get("document_uploaded_at", utc_now_iso()),
        pages=pages,
        results=results,
    )
    next_vault, status = add_document_to_vault(st.session_state["document_vault"], item)
    st.session_state["document_vault"] = next_vault
    _sync_vault_to_local_storage()

    if status == "duplicate":
        st.toast("이미 보관함에 저장된 문서입니다.")
    else:
        st.toast("문서가 보관함에 저장되었습니다.")


def _render_vault_toolbar() -> None:
    _ensure_vault_state()
    _sync_vault_to_local_storage()

    left, right = st.columns([0.72, 0.28], gap="large")
    with left:
        st.markdown("### 문서 진위 여부 판별")
        st.caption("분석 완료 문서는 최대 10개까지 보관함에 자동 저장됩니다.")
    with right:
        if st.button(
            f"보관함 {len(st.session_state['document_vault'])} / {MAX_VAULT_ITEMS}",
            use_container_width=True,
            key="document_vault_toggle",
        ):
            st.session_state["document_vault_open"] = not st.session_state["document_vault_open"]

    if st.session_state["document_vault_open"]:
        _render_document_vault_panel()


def _render_document_vault_panel() -> None:
    vault = st.session_state.get("document_vault", [])
    st.markdown(
        f"""
        <section class="vault-panel">
          <div class="vault-panel-title">
            <span>Document Vault</span>
            <strong>{len(vault)} / {MAX_VAULT_ITEMS} 저장됨</strong>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    search_col, sort_col = st.columns([0.62, 0.38], gap="medium")
    with search_col:
        query = st.text_input("보관함 검색", placeholder="문서 이름 검색", key="document_vault_search")
    with sort_col:
        sort_mode = st.selectbox(
            "정렬",
            ["최신순", "오래된순", "진위 여부별", "신뢰도순"],
            key="document_vault_sort",
        )

    visible_items = sort_vault_items(filter_vault_items(vault, query), sort_mode)
    if not visible_items:
        st.markdown(
            """
            <div class="vault-empty">
              <div class="vault-empty-icon">□</div>
              <strong>아직 저장된 문서가 없습니다.</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for item in visible_items:
        _render_vault_card(item)


def _render_vault_card(item: dict) -> None:
    document_id = item["id"]
    safe_name = html.escape(str(item.get("name", "문서")))
    analyzed_at = _format_timestamp(str(item.get("analyzed_at", "")))
    verdict = html.escape(str(item.get("verdict", "-")))
    confidence = int(item.get("confidence", 0))
    thumbnail = html.escape(str(item.get("thumbnail", "")))

    st.markdown(
        f"""
        <div class="vault-card">
          <img src="{thumbnail}" alt="{safe_name} 미리보기" />
          <div class="vault-card-body">
            <div class="vault-card-top">
              <strong>{safe_name}</strong>
              <span>{html.escape(str(item.get("document_type", "")))}</span>
            </div>
            <p>{analyzed_at}</p>
            <div class="vault-card-meta">
              <b>{verdict}</b>
              <span>신뢰도 {confidence}%</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    open_col, delete_col = st.columns([0.78, 0.22], gap="small")
    with open_col:
        if st.button("저장된 결과 열기", use_container_width=True, key=f"open_vault_{document_id}"):
            _open_vault_item(item)
            st.rerun()
    with delete_col:
        if st.button("휴지통", use_container_width=True, key=f"delete_vault_{document_id}"):
            st.session_state["pending_vault_delete"] = document_id

    if st.session_state.get("pending_vault_delete") == document_id:
        st.warning("정말 삭제하시겠습니까?")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("삭제", type="primary", use_container_width=True, key=f"confirm_delete_{document_id}"):
                st.session_state["document_vault"] = remove_document_from_vault(
                    st.session_state["document_vault"],
                    document_id,
                )
                st.session_state.pop("pending_vault_delete", None)
                _sync_vault_to_local_storage()
                st.toast("보관함에서 삭제되었습니다.")
                st.rerun()
        with cancel_col:
            if st.button("취소", use_container_width=True, key=f"cancel_delete_{document_id}"):
                st.session_state.pop("pending_vault_delete", None)
                st.rerun()


def _open_vault_item(item: dict) -> None:
    st.session_state["document_pages"] = item["pages"]
    st.session_state["document_name"] = item["name"]
    st.session_state["document_key"] = item["duplicate_key"]
    st.session_state["document_uploaded_at"] = item["uploaded_at"]
    st.session_state["analysis_results"] = item["results"]
    st.session_state["document_vault_open"] = False
    st.toast("저장된 분석 결과를 열었습니다.")


def _sync_vault_to_local_storage() -> None:
    payload = json.dumps(local_storage_payload(st.session_state.get("document_vault", [])), ensure_ascii=False)
    safe_payload = payload.replace("</", "<\\/")
    components.html(
        f"""
        <script>
        try {{
          window.parent.localStorage.setItem({json.dumps(VAULT_STORAGE_KEY)}, JSON.stringify({safe_payload}));
        }} catch (error) {{}}
        </script>
        """,
        height=0,
    )


def _format_timestamp(value: str) -> str:
    if not value:
        return "-"
    return value.replace("T", " ").replace("Z", "")


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
        pin_label = "핀 고정됨" if st.session_state.get("mvp_sidebar_pinned", True) else "핀 해제됨"
        if st.button(pin_label, help="사이드바를 항상 열어둘지 전환합니다.", use_container_width=True):
            st.session_state["mvp_sidebar_pinned"] = not st.session_state.get("mvp_sidebar_pinned", True)
            st.query_params["view"] = "mvp"
            st.query_params["sidebar"] = "pinned" if st.session_state["mvp_sidebar_pinned"] else "auto"
            st.rerun()

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
    max_suspicion_score = max(int(result["score"]) for result in results)
    trust_score = max(0, min(100, 100 - max_suspicion_score))
    high_page = max(results, key=lambda result: int(result["score"]))
    level_class = "low" if trust_score >= 75 else "warn" if trust_score >= 45 else "high"
    trust_label = "믿을 수 있음" if trust_score >= 75 else "검토 필요" if trust_score >= 45 else "주의 필요"

    st.markdown(
        f"""
        <div class="result-panel">
          <span class="panel-label">문서 신뢰 점수</span>
          <strong class="{level_class}">{trust_score}/100</strong>
          <p>점수가 높을수록 믿을 수 있는 문서에 가깝습니다. 현재 판정: <b>{trust_label}</b></p>
          <div class="score-guidance">
            <span>최고 의심 페이지 {high_page["page"]}페이지</span>
            <span>의심 신호 {max_suspicion_score}/100</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(trust_score / 100)

    page_labels = [f"{result['page']}페이지 · 신뢰 {100 - int(result['score'])}/100" for result in results]
    tabs = st.tabs(page_labels)

    for tab, result in zip(tabs, results):
        with tab:
            page_trust_score = max(0, min(100, 100 - int(result["score"])))
            st.markdown(f"#### {result['page']}페이지 분석 결과")
            st.caption(f"신뢰 점수 {page_trust_score}/100 · 의심 신호 {int(result['score'])}/100")
            st.image(result["result_image"], caption="빨간 박스: 추가 검토 후보", use_container_width=True)
            st.write(_translate_text(result["summary"]))
            for reason in result["reasons"]:
                st.markdown(f"- {_translate_text(reason)}")


def _render_web_results(capture_result: dict | None, url_result: dict | None) -> None:
    capture_suspicion_score = int(capture_result["score"]) if capture_result else 0
    capture_score = 100 - capture_suspicion_score if capture_result else 100
    url_score = int(url_result["trust_score"]) if url_result else 100
    trust_score = min(capture_score, url_score)
    risk_level = _web_risk_level(trust_score)
    level_class = "low" if trust_score >= 75 else "warn" if trust_score >= 45 else "high"
    trust_label = "믿을 수 있음" if trust_score >= 75 else "검토 필요" if trust_score >= 45 else "주의 필요"

    st.markdown(
        f"""
        <div class="result-panel">
          <span class="panel-label">웹 증거 신뢰도 점수</span>
          <strong class="{level_class}">{trust_score}/100</strong>
          <p>점수가 높을수록 믿을 수 있는 증거에 가깝습니다. 현재 판정: <b>{trust_label}</b> · 위험도: <b>{risk_level}</b></p>
          <div class="score-guidance">
            <span>캡처 신뢰도 {capture_score}/100</span>
            <span>URL 신뢰도 {url_score}/100</span>
          </div>
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
        :root {
            --dg-navy: #0a1628;
            --dg-blue: #2563eb;
            --dg-cyan: #22d3ee;
            --dg-ink: #0f172a;
            --dg-muted: #64748b;
            --dg-line: rgba(59, 130, 246, 0.16);
            --dg-glass: rgba(255, 255, 255, 0.72);
            --dg-shadow: 0 24px 70px rgba(15, 23, 42, 0.10);
        }
        .stApp {
            background:
                radial-gradient(circle at 12% 6%, rgba(34, 211, 238, 0.23), transparent 30%),
                radial-gradient(circle at 88% 0%, rgba(37, 99, 235, 0.18), transparent 34%),
                radial-gradient(circle at 70% 86%, rgba(14, 165, 233, 0.13), transparent 36%),
                linear-gradient(135deg, #f8fbff 0%, #eef5fb 42%, #f8fafc 100%);
            color: #0f172a;
            overflow-x: hidden;
        }
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu,
        header {
            visibility: hidden;
            height: 0;
        }
        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background-image:
                linear-gradient(rgba(37, 99, 235, 0.065) 1px, transparent 1px),
                linear-gradient(90deg, rgba(37, 99, 235, 0.055) 1px, transparent 1px),
                radial-gradient(circle at 20% 30%, rgba(34, 211, 238, 0.12) 0 2px, transparent 3px),
                radial-gradient(circle at 80% 20%, rgba(37, 99, 235, 0.10) 0 2px, transparent 3px);
            background-size: 72px 72px, 72px 72px, 180px 180px, 220px 220px;
            mask-image: linear-gradient(to bottom, rgba(0,0,0,0.8), rgba(0,0,0,0.22) 58%, transparent 100%);
            opacity: 0.9;
            animation: dgGridDrift 28s linear infinite;
        }
        .stApp::after {
            content: "";
            position: fixed;
            inset: auto -10% -28% -10%;
            height: 52vh;
            pointer-events: none;
            z-index: 0;
            background:
                radial-gradient(ellipse at 50% 55%, rgba(56, 189, 248, 0.18), transparent 58%),
                linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.10), transparent);
            filter: blur(28px);
            opacity: 0.8;
            animation: dgGlowFloat 18s ease-in-out infinite alternate;
        }
        [data-testid="stAppViewContainer"] > .main {
            position: relative;
            z-index: 1;
        }
        [data-testid="stAppViewContainer"] > .main .block-container {
            padding-top: 6.2rem;
            padding-bottom: 4rem;
            max-width: 1200px;
        }
        .mvp-navbar {
            position: fixed;
            top: 18px;
            left: calc(21rem + 24px);
            z-index: 999996;
            display: inline-flex;
            align-items: center;
            gap: 22px;
            min-height: 60px;
            padding: 0 30px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 20px;
            background:
                linear-gradient(145deg, rgba(255, 255, 255, 0.82), rgba(244, 249, 255, 0.68));
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(18px);
            animation: dgNavIn 250ms ease-out both;
            transition: left 300ms ease-in-out, right 300ms ease-in-out;
        }
        body.dg-sidebar-hidden .mvp-navbar {
            left: 24px;
        }
        body.dg-sidebar-open .mvp-navbar,
        body.dg-sidebar-pinned .mvp-navbar {
            left: calc(21rem + 24px);
        }
        .mvp-navbar a {
            position: relative;
            color: #0f172a !important;
            font-size: 19px;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-decoration: none !important;
            transition: color 200ms ease, opacity 200ms ease;
        }
        .mvp-navbar a::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: -7px;
            height: 2px;
            border-radius: 999px;
            background: #2563eb;
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 200ms ease;
        }
        .mvp-navbar a:hover {
            color: #2563eb !important;
        }
        .mvp-navbar a:hover::after {
            transform: scaleX(1);
        }
        .mvp-navbar-divider {
            width: 1px;
            height: 22px;
            background: rgba(148, 163, 184, 0.42);
        }
        .mvp-navbar strong {
            color: #1e293b;
            font-size: 21px;
            font-weight: 700;
            letter-spacing: 0;
            white-space: nowrap;
        }
        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(241, 247, 253, 0.78)),
                radial-gradient(circle at 20% 0%, rgba(34, 211, 238, 0.14), transparent 34%);
            border-right: 1px solid rgba(148, 163, 184, 0.22);
            backdrop-filter: blur(18px);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            color: var(--dg-ink);
        }
        [data-testid="stFileUploader"],
        [data-testid="stExpander"],
        div[data-testid="stForm"],
        div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stImage"]) {
            border-radius: 10px;
        }
        [data-testid="stFileUploader"] section {
            background: rgba(255, 255, 255, 0.66);
            border: 1px solid rgba(148, 163, 184, 0.28);
            box-shadow: 0 18px 48px rgba(15, 23, 42, 0.06);
            backdrop-filter: blur(16px);
        }
        [data-testid="stImage"] img {
            border-radius: 10px;
            box-shadow: 0 22px 60px rgba(15, 23, 42, 0.11);
            border: 1px solid rgba(148, 163, 184, 0.18);
        }
        div.stButton > button {
            min-height: 44px;
            border-radius: 8px;
            border: 1px solid rgba(37, 99, 235, 0.22);
            background:
                linear-gradient(135deg, rgba(37, 99, 235, 0.96), rgba(8, 145, 178, 0.94));
            color: #ffffff;
            box-shadow: 0 14px 30px rgba(37, 99, 235, 0.18);
            transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease;
        }
        div.stButton > button:hover {
            transform: translateY(-1px);
            filter: brightness(1.03);
            box-shadow: 0 18px 36px rgba(37, 99, 235, 0.22);
        }
        div.stButton > button:active {
            transform: translateY(0);
        }
        div[data-baseweb="input"] {
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.76);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
        }
        div[data-testid="stRadio"] label {
            border-radius: 8px;
        }
        .hero {
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            padding: 36px 40px;
            margin-bottom: 34px;
            background:
                linear-gradient(135deg, rgba(8, 20, 38, 0.94) 0%, rgba(13, 47, 72, 0.91) 52%, rgba(16, 93, 116, 0.88) 100%),
                radial-gradient(circle at 12% 0%, rgba(34, 211, 238, 0.24), transparent 34%),
                radial-gradient(circle at 90% 18%, rgba(59, 130, 246, 0.28), transparent 35%);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 10px;
            box-shadow: 0 30px 90px rgba(15, 23, 42, 0.18);
            backdrop-filter: blur(18px);
        }
        .hero::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
                linear-gradient(120deg, transparent 0 20%, rgba(125, 211, 252, 0.12) 20% 20.3%, transparent 20.6% 100%),
                linear-gradient(30deg, transparent 0 62%, rgba(255, 255, 255, 0.10) 62% 62.2%, transparent 62.6% 100%),
                radial-gradient(circle at 76% 42%, rgba(34, 211, 238, 0.22), transparent 18%);
            opacity: 0.82;
            animation: dgHeroLight 12s ease-in-out infinite alternate;
        }
        .hero::after {
            content: "";
            position: absolute;
            right: -80px;
            top: -120px;
            width: 360px;
            height: 360px;
            border: 1px solid rgba(125, 211, 252, 0.18);
            border-radius: 38% 62% 56% 44%;
            transform: rotate(24deg);
            background:
                linear-gradient(135deg, rgba(255,255,255,0.06), transparent),
                repeating-linear-gradient(60deg, rgba(255,255,255,0.10) 0 1px, transparent 1px 18px);
            opacity: 0.42;
        }
        .hero > * {
            position: relative;
            z-index: 1;
        }
        .hero h1 {
            margin: 0;
            font-size: 46px;
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
            color: rgba(224, 242, 254, 0.92);
            font-size: 19px;
        }
        .stage-badge {
            padding: 11px 15px;
            border: 1px solid rgba(255,255,255,0.30);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
            color: #ecfeff;
            white-space: nowrap;
        }
        .empty-state {
            padding: 42px;
            background: var(--dg-glass);
            border: 1px dashed rgba(59, 130, 246, 0.26);
            border-radius: 10px;
            text-align: center;
            box-shadow: var(--dg-shadow);
            backdrop-filter: blur(18px);
        }
        .empty-state h3 {
            margin-top: 0;
        }
        .result-panel {
            position: relative;
            overflow: hidden;
            padding: 24px;
            margin-top: 22px;
            background:
                linear-gradient(145deg, rgba(255,255,255,0.80), rgba(244, 249, 255, 0.68));
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 10px;
            box-shadow: var(--dg-shadow);
            backdrop-filter: blur(18px);
        }
        .result-panel::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
                linear-gradient(90deg, rgba(37, 99, 235, 0.18), transparent 34%),
                radial-gradient(circle at 88% 16%, rgba(34, 211, 238, 0.14), transparent 26%);
            opacity: 0.8;
        }
        .result-panel > * {
            position: relative;
            z-index: 1;
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
        .score-guidance {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }
        .score-guidance span {
            padding: 7px 10px;
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.62);
            color: #334155;
            font-size: 13px;
            font-weight: 700;
        }
        .vault-panel {
            position: relative;
            overflow: hidden;
            padding: 22px 24px;
            margin: 10px 0 18px;
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 10px;
            background:
                linear-gradient(145deg, rgba(255, 255, 255, 0.80), rgba(244, 249, 255, 0.66)),
                radial-gradient(circle at 92% 14%, rgba(34, 211, 238, 0.16), transparent 26%);
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(18px);
        }
        .vault-panel-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }
        .vault-panel-title span {
            color: #0f172a;
            font-size: 24px;
            font-weight: 800;
        }
        .vault-panel-title strong {
            color: #2563eb;
            font-size: 15px;
        }
        .vault-card {
            display: grid;
            grid-template-columns: 132px minmax(0, 1fr);
            gap: 18px;
            align-items: center;
            padding: 18px;
            margin-top: 14px;
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 10px;
            background: linear-gradient(145deg, rgba(255,255,255,0.78), rgba(241,247,253,0.58));
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07);
            backdrop-filter: blur(16px);
            transition: transform 160ms ease, box-shadow 160ms ease;
        }
        .vault-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 22px 54px rgba(37, 99, 235, 0.12);
        }
        .vault-card img {
            width: 132px;
            height: 92px;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid rgba(148, 163, 184, 0.20);
            background: #f8fafc;
        }
        .vault-card-body {
            min-width: 0;
        }
        .vault-card-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
        }
        .vault-card-top strong {
            overflow: hidden;
            color: #0f172a;
            font-size: 18px;
            font-weight: 800;
            line-height: 1.35;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .vault-card-top span {
            flex: 0 0 auto;
            padding: 4px 8px;
            border-radius: 999px;
            background: rgba(37, 99, 235, 0.08);
            color: #2563eb;
            font-size: 12px;
            font-weight: 800;
        }
        .vault-card-body p {
            margin: 8px 0 12px;
            color: #64748b;
            font-size: 13px;
        }
        .vault-card-meta {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .vault-card-meta b,
        .vault-card-meta span {
            display: inline-flex;
            align-items: center;
            min-height: 30px;
            padding: 0 10px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 800;
        }
        .vault-card-meta b {
            background: rgba(14, 165, 233, 0.12);
            color: #0369a1;
        }
        .vault-card-meta span {
            background: rgba(15, 23, 42, 0.06);
            color: #334155;
        }
        .vault-empty {
            display: grid;
            place-items: center;
            gap: 12px;
            padding: 44px 20px;
            margin: 18px 0 20px;
            border: 1px dashed rgba(37, 99, 235, 0.26);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.62);
            color: #334155;
            text-align: center;
            backdrop-filter: blur(14px);
        }
        .vault-empty-icon {
            display: grid;
            place-items: center;
            width: 48px;
            height: 48px;
            border-radius: 12px;
            border: 1px solid rgba(37, 99, 235, 0.22);
            color: #2563eb;
            font-size: 28px;
            font-weight: 800;
        }
        hr {
            border-color: rgba(148, 163, 184, 0.20);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.22);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            color: var(--dg-muted);
        }
        .stTabs [aria-selected="true"] {
            color: var(--dg-blue);
            background: rgba(255, 255, 255, 0.56);
        }
        .landing-shell {
            position: relative;
            z-index: 1;
            color: #0f172a;
        }
        .landing-shell::before {
            content: "";
            position: fixed;
            inset: 0;
            z-index: -1;
            pointer-events: none;
            background:
                linear-gradient(115deg, rgba(255,255,255,0.98) 0%, rgba(241,247,253,0.92) 40%, rgba(226,241,255,0.80) 100%),
                radial-gradient(ellipse at 16% 12%, rgba(56, 189, 248, 0.24), transparent 34%),
                radial-gradient(ellipse at 88% 18%, rgba(37, 99, 235, 0.18), transparent 35%),
                radial-gradient(ellipse at 56% 92%, rgba(6, 182, 212, 0.14), transparent 40%);
        }
        .landing-shell::after {
            content: "";
            position: fixed;
            inset: 0;
            z-index: -1;
            pointer-events: none;
            opacity: 0.72;
            background-image:
                linear-gradient(rgba(37, 99, 235, 0.07) 1px, transparent 1px),
                linear-gradient(90deg, rgba(37, 99, 235, 0.06) 1px, transparent 1px),
                linear-gradient(135deg, transparent 0 48%, rgba(56, 189, 248, 0.10) 48.1% 48.4%, transparent 48.5%);
            background-size: 72px 72px, 72px 72px, 220px 220px;
            mask-image: linear-gradient(to bottom, rgba(0,0,0,0.78), rgba(0,0,0,0.36) 62%, transparent 100%);
            animation: dgGridDrift 32s linear infinite;
        }
        .landing-hero {
            position: relative;
            display: grid;
            grid-template-columns: minmax(0, 0.92fr) minmax(420px, 1.08fr);
            align-items: center;
            min-height: 620px;
            column-gap: 54px;
            row-gap: 28px;
            padding: 58px 0 74px;
        }
        .landing-hero::before {
            content: "";
            position: absolute;
            inset: 4% -5% 8%;
            z-index: -1;
            background:
                linear-gradient(120deg, rgba(15, 23, 42, 0.05), transparent 36%),
                radial-gradient(ellipse at 72% 42%, rgba(37, 99, 235, 0.16), transparent 42%);
            filter: blur(18px);
        }
        .hero-copy h1 {
            margin: 0 0 16px;
            color: #0f172a;
            font-size: 72px;
            line-height: 1;
            letter-spacing: 0;
        }
        .hero-copy h2 {
            margin: 0;
            color: #1e293b;
            font-size: 34px;
            line-height: 1.22;
            font-weight: 700;
            letter-spacing: 0;
        }
        .hero-copy p {
            max-width: 560px;
            margin: 30px 0 0;
            color: #475569;
            font-size: 22px;
            line-height: 1.78;
        }
        .hero-visual {
            position: relative;
            min-height: 500px;
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 8px;
            overflow: hidden;
            background:
                radial-gradient(ellipse at 50% 42%, rgba(56, 189, 248, 0.22), transparent 38%),
                linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92) 48%, rgba(15, 91, 124, 0.82));
            box-shadow: 0 36px 110px rgba(15, 23, 42, 0.22);
        }
        .hero-visual::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.20), transparent),
                repeating-linear-gradient(0deg, rgba(255,255,255,0.08) 0 1px, transparent 1px 34px),
                repeating-linear-gradient(90deg, rgba(255,255,255,0.065) 0 1px, transparent 1px 34px);
            opacity: 0.5;
            animation: dgGradientMotion 10s ease-in-out infinite alternate;
        }
        .hero-visual::after {
            content: "";
            position: absolute;
            inset: 14%;
            border: 1px solid rgba(125, 211, 252, 0.18);
            background:
                linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.03)),
                repeating-linear-gradient(135deg, transparent 0 18px, rgba(56,189,248,0.12) 19px 20px);
            transform: perspective(800px) rotateX(58deg) rotateZ(-12deg);
            filter: drop-shadow(0 0 28px rgba(56, 189, 248, 0.28));
        }
        .visual-grid {
            position: absolute;
            inset: 0;
            background:
                linear-gradient(120deg, transparent 0 28%, rgba(96, 165, 250, 0.16) 28.2% 28.5%, transparent 28.7%),
                linear-gradient(42deg, transparent 0 63%, rgba(6, 182, 212, 0.20) 63.1% 63.5%, transparent 63.7%);
            animation: dgHeroLight 12s ease-in-out infinite alternate;
        }
        .network-map {
            position: absolute;
            inset: 54px 32px auto;
            width: calc(100% - 64px);
            height: 360px;
            overflow: visible;
        }
        .network-map path {
            fill: none;
            stroke: url(#lineFlow);
            stroke-width: 2;
            stroke-linecap: round;
            filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.35));
            stroke-dasharray: 9 13;
            animation: dgDash 14s linear infinite;
        }
        .network-map circle {
            fill: #e0f2fe;
            stroke: rgba(56, 189, 248, 0.92);
            stroke-width: 3;
            filter: drop-shadow(0 0 14px rgba(56, 189, 248, 0.58));
            animation: dgPulse 2.8s ease-in-out infinite alternate;
        }
        .scan-card {
            position: absolute;
            width: 190px;
            padding: 18px;
            border: 1px solid rgba(226, 232, 240, 0.22);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.10);
            color: #e0f2fe;
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.22);
            backdrop-filter: blur(18px);
            animation: dgFloat 7s ease-in-out infinite;
        }
        .scan-card span {
            display: block;
            color: rgba(224, 242, 254, 0.72);
            font-size: 12px;
            margin-bottom: 8px;
        }
        .scan-card strong {
            display: block;
            font-size: 25px;
            letter-spacing: 0;
        }
        .scan-card i {
            display: block;
            height: 3px;
            margin-top: 14px;
            border-radius: 999px;
            background: linear-gradient(90deg, #38bdf8, #60a5fa, transparent);
            box-shadow: 0 0 18px rgba(56, 189, 248, 0.42);
        }
        .card-a {
            right: 34px;
            top: 54px;
        }
        .card-b {
            left: 36px;
            bottom: 42px;
            animation-delay: -2.4s;
        }
        .landing-section {
            padding: 78px 0;
        }
        .feature-grid,
        .compare-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px;
        }
        .glass-feature,
        .compare-card,
        .timeline-step {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 8px;
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.76), rgba(241, 247, 253, 0.54));
            box-shadow: 0 24px 70px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(18px);
        }
        .glass-feature {
            min-height: 250px;
            padding: 36px;
            transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
        }
        .glass-feature::before,
        .compare-card::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(110deg, rgba(37, 99, 235, 0.12), transparent 38%),
                radial-gradient(ellipse at 80% 18%, rgba(56, 189, 248, 0.16), transparent 30%);
            opacity: 0;
            transition: opacity 180ms ease;
        }
        .glass-feature:hover {
            transform: translateY(-6px);
            border-color: rgba(37, 99, 235, 0.30);
            box-shadow: 0 30px 86px rgba(37, 99, 235, 0.14);
        }
        .glass-feature:hover::before,
        .compare-card.after::before {
            opacity: 1;
        }
        .glass-feature > *,
        .compare-card > * {
            position: relative;
            z-index: 1;
        }
        .feature-icon {
            display: grid;
            place-items: center;
            width: 48px;
            height: 48px;
            border: 1px solid rgba(37, 99, 235, 0.20);
            border-radius: 8px;
            background: rgba(37, 99, 235, 0.08);
            color: #2563eb;
            font-weight: 800;
            margin-bottom: 26px;
        }
        .glass-feature h3,
        .compare-card h3,
        .timeline-step h3 {
            margin: 0 0 12px;
            color: #0f172a;
            font-size: 32px;
            line-height: 1.22;
        }
        .glass-feature p {
            margin: 0;
            color: #475569;
            font-size: 18px;
            line-height: 1.75;
        }
        .timeline-step h3 {
            font-size: 26px;
            line-height: 1.38;
            font-weight: 700;
            letter-spacing: -0.2px;
            white-space: nowrap;
        }
        .timeline {
            position: relative;
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 18px;
        }
        .timeline::before {
            content: "";
            position: absolute;
            left: 8%;
            right: 8%;
            top: 50%;
            height: 2px;
            background: linear-gradient(90deg, rgba(37, 99, 235, 0.12), rgba(56, 189, 248, 0.62), rgba(37, 99, 235, 0.12));
            box-shadow: 0 0 28px rgba(56, 189, 248, 0.24);
        }
        .timeline-step {
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 220px;
            padding: 44px;
            animation: dgRise 700ms ease both;
        }
        .flow-icon {
            position: absolute;
            right: 22px;
            top: 22px;
            width: 34px;
            height: 34px;
            color: #2563eb;
            opacity: 0.78;
            filter: drop-shadow(0 0 14px rgba(56, 189, 248, 0.18));
        }
        .flow-icon path {
            fill: none;
            stroke: currentColor;
            stroke-width: 1.7;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .timeline-step b {
            display: grid;
            place-items: center;
            width: 54px;
            height: 54px;
            margin-bottom: 28px;
            border-radius: 999px;
            color: #ffffff;
            background: linear-gradient(135deg, #2563eb, #06b6d4);
            box-shadow: 0 16px 34px rgba(37, 99, 235, 0.24);
            font-size: 17px;
            font-weight: 800;
        }
        .compare-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .compare-card {
            padding: 46px;
            min-height: 390px;
        }
        .compare-card.before {
            background:
                linear-gradient(145deg, rgba(248, 250, 252, 0.90), rgba(226, 232, 240, 0.70)),
                repeating-linear-gradient(0deg, rgba(15, 23, 42, 0.026) 0 1px, transparent 1px 8px),
                repeating-linear-gradient(90deg, rgba(100, 116, 139, 0.022) 0 1px, transparent 1px 10px);
            box-shadow: 0 22px 64px rgba(15, 23, 42, 0.07);
        }
        .compare-card.before::before {
            opacity: 1;
            background:
                radial-gradient(circle at 18% 12%, rgba(148, 163, 184, 0.14), transparent 28%),
                linear-gradient(130deg, rgba(255, 255, 255, 0.42), transparent 52%);
        }
        .compare-card.before::after {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background-image:
                radial-gradient(circle, rgba(71, 85, 105, 0.10) 0 1px, transparent 1.4px);
            background-size: 22px 22px;
            opacity: 0.22;
        }
        .compare-card span {
            display: block;
            color: #64748b;
            font-size: 32px;
            line-height: 1.35;
            font-weight: 800;
            letter-spacing: 0.01em;
            margin-bottom: 14px;
        }
        .compare-card h3 {
            font-size: 34px;
            line-height: 1.35;
            font-weight: 800;
            letter-spacing: 0.01em;
        }
        .compare-card ul {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
            padding: 0;
            margin: 34px 0 0;
            list-style: none;
        }
        .compare-card li {
            padding: 18px 20px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.58);
            color: #334155;
            font-size: 23px;
            line-height: 1.55;
            font-weight: 600;
            letter-spacing: 0.01em;
        }
        .compare-card.after {
            border-color: rgba(37, 99, 235, 0.32);
            background:
                radial-gradient(circle at 78% 18%, rgba(56, 189, 248, 0.24), transparent 30%),
                radial-gradient(circle at 18% 84%, rgba(37, 99, 235, 0.16), transparent 34%),
                linear-gradient(145deg, rgba(255, 255, 255, 0.82), rgba(226, 241, 255, 0.62));
            box-shadow: 0 30px 88px rgba(37, 99, 235, 0.13);
        }
        .compare-card.after span {
            color: #2563eb;
        }
        .compare-card.after::before {
            opacity: 1;
            background:
                linear-gradient(rgba(37, 99, 235, 0.07) 1px, transparent 1px),
                linear-gradient(90deg, rgba(37, 99, 235, 0.06) 1px, transparent 1px),
                linear-gradient(115deg, transparent 0 48%, rgba(56, 189, 248, 0.18) 48.1% 48.35%, transparent 48.5%);
            background-size: 34px 34px, 34px 34px, 180px 180px;
        }
        .compare-card.after::after {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background:
                radial-gradient(circle at 18% 22%, rgba(56, 189, 248, 0.30) 0 2px, transparent 3px),
                radial-gradient(circle at 72% 34%, rgba(37, 99, 235, 0.24) 0 2px, transparent 3px),
                radial-gradient(circle at 88% 78%, rgba(6, 182, 212, 0.22) 0 2px, transparent 3px);
            background-size: 120px 120px, 150px 150px, 180px 180px;
            opacity: 0.54;
        }
        .landing-cta {
            position: relative;
            overflow: hidden;
            margin: 54px 0 24px;
            padding: 78px 34px 56px;
            text-align: center;
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.94) 52%, rgba(14, 116, 144, 0.86)),
                radial-gradient(ellipse at 50% 0%, rgba(56, 189, 248, 0.28), transparent 38%);
            box-shadow: 0 34px 100px rgba(15, 23, 42, 0.20);
        }
        .landing-cta::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(90deg, transparent, rgba(56, 189, 248, 0.16), transparent),
                repeating-linear-gradient(90deg, transparent 0 42px, rgba(255,255,255,0.08) 43px 44px);
            animation: dgGradientMotion 11s ease-in-out infinite alternate;
        }
        .landing-cta > * {
            position: relative;
            z-index: 1;
        }
        .landing-cta p {
            max-width: 760px;
            margin: 0 auto;
            color: rgba(224, 242, 254, 0.84);
            font-size: 30px;
            line-height: 1.75;
            font-weight: 700;
        }
        .landing-cta-button {
            position: relative;
            z-index: 1;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
            min-width: 360px;
            min-height: 78px;
            margin-top: 42px;
            padding: 0 42px;
            border-radius: 999px;
            border: 1px solid rgba(224, 242, 254, 0.32);
            color: #ffffff !important;
            font-size: 24px;
            font-weight: 800;
            text-decoration: none !important;
            background: linear-gradient(135deg, #2563eb, #38bdf8 52%, #06b6d4);
            box-shadow: 0 18px 46px rgba(37, 99, 235, 0.34), 0 0 32px rgba(56, 189, 248, 0.22);
            transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
        }
        .landing-cta-button svg {
            width: 28px;
            height: 28px;
            color: #ffffff;
            flex: 0 0 auto;
            transition: transform 240ms ease-out;
        }
        .landing-cta-button svg path {
            fill: none;
            stroke: currentColor;
            stroke-width: 2.8;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .landing-cta-button:hover {
            transform: translateY(-2px) scale(1.03);
            filter: brightness(1.06);
            box-shadow: 0 30px 72px rgba(37, 99, 235, 0.46), 0 0 56px rgba(56, 189, 248, 0.42);
        }
        .landing-cta-button:hover svg {
            transform: translateX(5px);
        }
        .hero-cta-button {
            grid-column: 2;
            justify-self: center;
            margin-top: 0;
        }
        .reveal {
            animation: dgReveal 760ms ease both;
        }
        .reveal:nth-child(2) { animation-delay: 90ms; }
        .reveal:nth-child(3) { animation-delay: 160ms; }
        .reveal:nth-child(4) { animation-delay: 220ms; }
        .reveal:nth-child(5) { animation-delay: 280ms; }
        @keyframes dgGridDrift {
            from { background-position: 0 0, 0 0, 0 0, 0 0; }
            to { background-position: 72px 72px, -72px 72px, 36px 72px, -44px 88px; }
        }
        @keyframes dgGlowFloat {
            from { transform: translate3d(-1.5%, 0, 0) scale(1); opacity: 0.72; }
            to { transform: translate3d(1.5%, -2%, 0) scale(1.04); opacity: 0.88; }
        }
        @keyframes dgHeroLight {
            from { opacity: 0.62; transform: translateX(-8px); }
            to { opacity: 0.95; transform: translateX(8px); }
        }
        @keyframes dgReveal {
            from { opacity: 0; transform: translateY(22px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes dgGradientMotion {
            from { transform: translateX(-4%); opacity: 0.44; }
            to { transform: translateX(4%); opacity: 0.82; }
        }
        @keyframes dgDash {
            to { stroke-dashoffset: -180; }
        }
        @keyframes dgPulse {
            from { opacity: 0.72; transform: scale(0.98); }
            to { opacity: 1; transform: scale(1.04); }
        }
        @keyframes dgFloat {
            0%, 100% { transform: translate3d(0, 0, 0); }
            50% { transform: translate3d(0, -10px, 0); }
        }
        @keyframes dgRise {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes dgNavIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 800px) {
            [data-testid="stAppViewContainer"] > .main .block-container {
                padding-top: 5.6rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .mvp-navbar {
                top: 12px;
                left: 12px;
                right: 12px;
                min-height: 56px;
                padding: 0 20px;
                gap: 16px;
            }
            .mvp-navbar a {
                font-size: 18px;
            }
            .mvp-navbar strong {
                font-size: 20px;
            }
            .hero {
                display: grid;
                grid-template-columns: 1fr;
                padding: 28px 24px;
            }
            .hero h1 {
                font-size: 34px;
            }
            .stage-badge {
                white-space: normal;
            }
            .vault-panel-title,
            .vault-card,
            .vault-card-top {
                display: grid;
                grid-template-columns: 1fr;
            }
            .vault-card img {
                width: 100%;
                height: 150px;
            }
            .landing-hero,
            .feature-grid,
            .timeline,
            .compare-grid {
                grid-template-columns: 1fr;
            }
            .landing-hero {
                min-height: auto;
                column-gap: 0;
                row-gap: 28px;
                padding: 36px 0 46px;
            }
            .hero-copy h1 {
                font-size: 42px;
                line-height: 1.04;
            }
            .hero-copy h2 {
                font-size: 22px;
                line-height: 1.28;
            }
            .hero-copy p {
                margin-top: 22px;
                font-size: 17px;
                line-height: 1.78;
            }
            .landing-section {
                padding: 56px 0;
            }
            .glass-feature,
            .compare-card,
            .timeline-step {
                padding: 28px;
            }
            .glass-feature h3,
            .compare-card h3 {
                font-size: 24px;
            }
            .glass-feature p,
            .compare-card li {
                font-size: 18px;
                line-height: 1.6;
                font-weight: 600;
            }
            .timeline-step h3 {
                font-size: 21px;
                line-height: 1.42;
                font-weight: 700;
                letter-spacing: -0.2px;
                white-space: normal;
            }
            .timeline-step {
                min-height: 178px;
            }
            .timeline-step b {
                width: 48px;
                height: 48px;
                margin-bottom: 22px;
                font-size: 15px;
            }
            .compare-card span,
            .compare-card h3 {
                font-size: 24px;
                line-height: 1.45;
                font-weight: 800;
                letter-spacing: 0.01em;
            }
            .hero-visual {
                min-height: 380px;
            }
            .timeline::before {
                left: 32px;
                right: auto;
                top: 26px;
                bottom: 26px;
                width: 2px;
                height: auto;
            }
            .compare-card ul {
                grid-template-columns: 1fr;
            }
            .landing-cta {
                padding: 56px 22px 36px;
            }
            .landing-cta p {
                font-size: 24px;
                line-height: 1.72;
            }
            .landing-cta-button {
                min-width: 100%;
                min-height: 72px;
                font-size: 22px;
                padding: 0 24px;
            }
            .landing-cta-button svg {
                width: 22px;
                height: 22px;
            }
            .hero-cta-button {
                grid-column: 1;
                justify-self: stretch;
            }
        }
        @media (min-width: 801px) and (max-width: 1100px) {
            .landing-hero {
                grid-template-columns: 1fr;
            }
            .hero-copy h1 {
                font-size: 56px;
                line-height: 1.02;
            }
            .hero-copy h2 {
                font-size: 28px;
            }
            .hero-copy p {
                font-size: 20px;
                line-height: 1.78;
            }
            .feature-grid,
            .timeline {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .glass-feature {
                padding: 32px;
            }
            .compare-card,
            .timeline-step {
                padding: 36px;
            }
            .glass-feature h3,
            .compare-card h3 {
                font-size: 28px;
            }
            .glass-feature p,
            .compare-card li {
                font-size: 20px;
                line-height: 1.58;
                font-weight: 600;
            }
            .timeline-step h3 {
                font-size: 23px;
                line-height: 1.4;
                font-weight: 700;
                letter-spacing: -0.2px;
                white-space: nowrap;
            }
            .compare-card span,
            .compare-card h3 {
                font-size: 28px;
                line-height: 1.42;
                font-weight: 800;
            }
            .timeline-step {
                min-height: 198px;
            }
            .timeline-step b {
                width: 50px;
                height: 50px;
                margin-bottom: 24px;
            }
            .landing-cta p {
                font-size: 28px;
            }
            .timeline::before {
                display: none;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

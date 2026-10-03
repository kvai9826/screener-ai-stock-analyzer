import streamlit as st
import pandas as pd
from config import Config
from screener_fetcher import ScreenerFetcher
from news_search import NewsFetcher
from ai_analyst import AIStockAnalyst
from utils import extract_ticker

# Streamlit Page Configuration
st.set_page_config(
    page_title="Screener AI Stock Analyzer & Comparison Engine",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Screener.in AI Stock Analyzer & Comparison Engine")
st.markdown("Automated Financial Extraction + Global Web Headlines + OpenRouter Free AI Models")

# Initialize modules
fetcher = ScreenerFetcher()
news_fetcher = NewsFetcher()

# Cached Read-Only Data Fetchers
@st.cache_data(ttl=Config.CACHE_TTL_SECONDS, show_spinner=False)
def cached_get_company_data(ticker: str):
    return fetcher.get_company_data(ticker)

@st.cache_data(ttl=Config.CACHE_TTL_SECONDS, show_spinner=False)
def cached_get_stock_news(company_name: str, limit: int, freshness_days: int):
    return news_fetcher.get_stock_news(company_name, limit=limit, freshness_days=freshness_days)

@st.cache_data(ttl=Config.CACHE_TTL_SECONDS, show_spinner=False)
def cached_get_chart_data(company_id: str):
    return fetcher.get_chart_data(company_id)

# Sidebar - API Credentials & Settings (OpenRouter & Free Models Only)
st.sidebar.header("🔑 OpenRouter AI Credentials")
openrouter_key = st.sidebar.text_input(
    "OpenRouter API Key (Free)",
    value=Config.OPENROUTER_API_KEY,
    type="password",
    help="Get free API key from openrouter.ai/keys"
)

gemma_model = st.sidebar.selectbox(
    "Select Free AI Model:",
    [
        Config.OPENROUTER_MODEL,
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "deepseek/deepseek-r1:free",
        "openrouter/free"
    ],
    index=0,
    help="OpenRouter free model tier"
)

news_freshness = st.sidebar.select_slider(
    "📰 News Freshness Filter:",
    options=[1, 7, 30],
    value=Config.DEFAULT_NEWS_FRESHNESS_DAYS,
    format_func=lambda x: f"Last {x} Day{'s' if x > 1 else ''}"
)

analyst = AIStockAnalyst(
    openrouter_api_key=openrouter_key, 
    model=gemma_model
)

# App Mode Selector
mode = st.radio("Choose App Mode:", ["🔍 Single Stock Deep Analysis", "⚔️ Compare Two Stocks"], horizontal=True)

st.markdown("---")

# ==============================================================================
# MODE 1: SINGLE STOCK DEEP ANALYSIS
# ==============================================================================
if mode == "🔍 Single Stock Deep Analysis":
    st.subheader("🔎 Search Stock with Autocomplete")

    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search_term = st.text_input(
            "Type Stock Name or Ticker (e.g. Reliance, TCS, Infosys, HDFC, Tata Motors):",
            value="",
            placeholder="Type a stock name to search Screener.in..."
        )

    # Dynamic Autocomplete Dropdown
    selected_company_info = None
    if search_term.strip():
        search_results = fetcher.search_company(search_term.strip())
        if search_results:
            options = {f"{item['name']} ({extract_ticker(item['url'])})": item for item in search_results}
            selected_option = st.selectbox("Select Matching Stock from Dropdown:", list(options.keys()))
            selected_company_info = options[selected_option]

    with col_btn:
        st.write("")
        st.write("")
        analyze_btn = st.button("🚀 Analyze Stock", use_container_width=True)

    # Blank Landing Page state
    if not selected_company_info and 'analysis_data' not in st.session_state:
        st.info("👋 **Welcome to Screener AI Stock Analyzer!**")
        st.markdown("""
        ### How to use this tool:
        1. **Type a stock name or ticker** in the search box above (e.g., `RELIANCE`, `TCS`, `INFY`, `TATAMOTORS`).
        2. **Select the matching company** from the dropdown menu.
        3. Click **🚀 Analyze Stock** to trigger QoQ Financial Extraction, FII/DII Shareholding, Piotroski Health Score, and AI Report generation.
        """)
        
        st.markdown("#### ⚡ Quick Example Stocks:")
        col_ex1, col_ex2, col_ex3, col_ex4 = st.columns(4)
        if col_ex1.button("📌 Reliance Industries"):
            st.session_state['quick_search'] = "RELIANCE"
            st.rerun()
        if col_ex2.button("📌 TCS"):
            st.session_state['quick_search'] = "TCS"
            st.rerun()
        if col_ex3.button("📌 Infosys"):
            st.session_state['quick_search'] = "INFY"
            st.rerun()
        if col_ex4.button("📌 Tata Motors"):
            st.session_state['quick_search'] = "TATAMOTORS"
            st.rerun()

    # Handle quick search button clicks
    if 'quick_search' in st.session_state and st.session_state['quick_search'] and not selected_company_info:
        quick_results = fetcher.search_company(st.session_state['quick_search'])
        if quick_results:
            selected_company_info = quick_results[0]
            st.session_state['quick_search'] = None

    # Trigger analysis strictly on Analyze Stock button click
    if analyze_btn and selected_company_info:
        ticker = extract_ticker(selected_company_info['url'])
        company_id = selected_company_info.get('id', '')

        with st.spinner(f"Fetching financial statements & web news for {selected_company_info['name']}..."):
            c_data = cached_get_company_data(ticker)
            n_data = cached_get_stock_news(selected_company_info['name'], limit=8, freshness_days=news_freshness)
            ch_data = cached_get_chart_data(company_id) if company_id else {}

            report = analyst.generate_analysis(
                c_data['name'],
                c_data['top_ratios'],
                c_data['tables'],
                n_data,
                ch_data
            )

            st.session_state['analysis_data'] = {
                'info': selected_company_info,
                'ticker': ticker,
                'company_data': c_data,
                'news_articles': n_data,
                'chart_data': ch_data,
                'report': report,
                'provider_used': analyst.last_provider_used,
                'error': analyst.last_error
            }

    # Render persisted analysis from session state
    if 'analysis_data' in st.session_state:
        res = st.session_state['analysis_data']
        c_data = res['company_data']
        n_data = res['news_articles']
        ch_data = res['chart_data']
        tables = c_data['tables']
        scores = c_data.get('health_scores', {})

        basis_str = "Consolidated Financials" if c_data.get('is_consolidated') else "Standalone Financials"

        st.markdown(f"## 📌 {c_data['name']} (`{res['ticker']}`)")
        st.caption(f"📊 Reporting Basis: **{basis_str}** | 🛡️ {scores.get('health_label', '')} (Piotroski F-Score: **{scores.get('piotroski_f_score', 0)}/9**)")

        # Manage Quick Ratios Custom Selector (Just like Screener.in's Manage quick_ratios)
        all_metrics = c_data.get('all_metrics', c_data.get('top_ratios', {}))
        top_ratios = c_data.get('top_ratios', {})
        all_keys = list(all_metrics.keys())
        default_keys = list(top_ratios.keys())

        with st.expander("⚙️ Manage Quick Ratios / Filter Display Metrics", expanded=False):
            st.markdown("Choose which ratios and financial statement metrics to display on your stock dashboard cards:")
            selected_keys = st.multiselect(
                "Filter & Select Display Ratios:",
                options=all_keys,
                default=st.session_state.get('custom_ratios', default_keys),
                key="ratio_multiselect"
            )
            st.session_state['custom_ratios'] = selected_keys

        active_keys = st.session_state.get('custom_ratios', default_keys)
        
        # Render Selected Quick Ratio Cards
        if active_keys:
            st.markdown("### 📊 Key Financial Ratios")
            cols = st.columns(min(len(active_keys), 4))
            for idx, k in enumerate(active_keys):
                v = all_metrics.get(k, 'N/A')
                with cols[idx % 4]:
                    st.metric(label=k, value=v)

        st.markdown("---")

        # Tabs Layout
        tab_ai, tab_qoq, tab_fii, tab_statements, tab_chart, tab_news = st.tabs([
            "🤖 Deep AI Report & Decision Matrix", 
            "📊 Quarterly Results (QoQ)",
            "🤝 FII / DII Shareholding",
            "📑 Annual Financial Statements", 
            "📈 Price & DMA Chart", 
            "🌐 Global Headlines & News"
        ])

        # Tab 1: AI Report
        with tab_ai:
            st.markdown(f"### 🤖 AI Equity Research Report ({gemma_model})")
            if res.get('error'):
                st.warning(f"⚠️ {res['error']}")
            st.info(f"⚙️ **Engine Provider Used:** `{res.get('provider_used', 'N/A')}`")
            st.markdown(res['report'])

        # Tab 2: QoQ Financials
        with tab_qoq:
            st.markdown("### 📊 Quarterly Financial Results (QoQ)")
            st.caption(f"Extracted directly from Screener.in ({basis_str})")
            if tables.get('quarters') is not None and not tables['quarters'].empty:
                st.dataframe(tables['quarters'], use_container_width=True)
            else:
                st.info("Quarterly results table not available for this stock.")

        # Tab 3: Shareholding Pattern
        with tab_fii:
            st.markdown("### 🤝 Shareholding Pattern & FII / DII Trends")
            st.caption("Extracted directly from Screener.in")
            if tables.get('shareholding') is not None and not tables['shareholding'].empty:
                st.dataframe(tables['shareholding'], use_container_width=True)
            else:
                st.info("Shareholding pattern table not available for this stock.")

        # Tab 4: Annual Financial Statements
        with tab_statements:
            st.markdown("### 📑 Annual Financial Statements")
            pnl_tab, bs_tab, cf_tab = st.tabs(["Profit & Loss Statement", "Balance Sheet", "Cash Flow Statement"])

            with pnl_tab:
                if tables.get('profit_loss') is not None and not tables['profit_loss'].empty:
                    st.dataframe(tables['profit_loss'], use_container_width=True)
                else:
                    st.info("Profit & Loss statement not available.")

            with bs_tab:
                if tables.get('balance_sheet') is not None and not tables['balance_sheet'].empty:
                    st.dataframe(tables['balance_sheet'], use_container_width=True)
                else:
                    st.info("Balance sheet not available.")

            with cf_tab:
                if tables.get('cash_flow') is not None and not tables['cash_flow'].empty:
                    st.dataframe(tables['cash_flow'], use_container_width=True)
                else:
                    st.info("Cash flow statement not available.")

        # Tab 5: Chart
        with tab_chart:
            st.markdown("### 📈 Historical Price & Moving Averages (1 Year)")
            datasets = ch_data.get('datasets', [])
            if datasets:
                chart_dfs = []
                for ds in datasets:
                    metric_name = ds.get('label', ds.get('metric', 'Value'))
                    vals = ds.get('values', [])
                    if vals:
                        df_ds = pd.DataFrame(vals, columns=['Date', metric_name])
                        df_ds['Date'] = pd.to_datetime(df_ds['Date'])
                        df_ds[metric_name] = pd.to_numeric(df_ds[metric_name], errors='coerce')
                        df_ds = df_ds.set_index('Date')
                        chart_dfs.append(df_ds)

                if chart_dfs:
                    merged_chart = pd.concat(chart_dfs, axis=1)
                    st.line_chart(merged_chart)
            else:
                st.info("Chart data not available for this ticker.")

        # Tab 6: News
        with tab_news:
            st.markdown(f"### 🌐 Web News Headlines (Last {news_freshness} Days)")
            if n_data:
                for article in n_data:
                    st.markdown(f"#### [{article['title']}]({article['link']})")
                    st.caption(f"🗓️ Published: {article['date']} | 📰 Source: {article['source']}")
                    st.markdown("---")
            else:
                st.info("No recent news articles found for this company.")

# ==============================================================================
# MODE 2: COMPARE TWO STOCKS
# ==============================================================================
elif mode == "⚔️ Compare Two Stocks":
    st.subheader("⚔️ Head-to-Head Stock Comparison")

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        s1_input = st.text_input("Stock 1 (e.g. RELIANCE, TCS, TATAMOTORS):", value="", placeholder="Type Stock 1...", key="s1_in")
        s1_results = fetcher.search_company(s1_input) if s1_input.strip() else []
        s1_info = None
        if s1_results:
            opts1 = {f"{item['name']} ({extract_ticker(item['url'])})": item for item in s1_results}
            sel1 = st.selectbox("Select Stock 1 Dropdown:", list(opts1.keys()), key="s1_sel")
            s1_info = opts1[sel1]

    with col_s2:
        s2_input = st.text_input("Stock 2 (e.g. TCS, INFY, M&M):", value="", placeholder="Type Stock 2...", key="s2_in")
        s2_results = fetcher.search_company(s2_input) if s2_input.strip() else []
        s2_info = None
        if s2_results:
            opts2 = {f"{item['name']} ({extract_ticker(item['url'])})": item for item in s2_results}
            sel2 = st.selectbox("Select Stock 2 Dropdown:", list(opts2.keys()), key="s2_sel")
            s2_info = opts2[sel2]

    compare_btn = st.button("⚔️ Run Head-to-Head Comparison", use_container_width=True)

    if compare_btn and s1_info and s2_info:
        t1 = extract_ticker(s1_info['url'])
        t2 = extract_ticker(s2_info['url'])

        with st.spinner(f"Extracting side-by-side data for {s1_info['name']} vs {s2_info['name']}..."):
            d1 = cached_get_company_data(t1)
            d2 = cached_get_company_data(t2)

            comp_report = analyst.generate_analysis(
                s1_info['name'], d1['top_ratios'], d1['tables'], []
            )

            st.session_state['comparison_data'] = {
                's1_info': s1_info,
                's2_info': s2_info,
                'd1': d1,
                'd2': d2,
                'report': comp_report,
                'provider_used': analyst.last_provider_used,
                'error': analyst.last_error
            }

    if 'comparison_data' in st.session_state:
        c_res = st.session_state['comparison_data']
        s1_info = c_res['s1_info']
        s2_info = c_res['s2_info']
        d1 = c_res['d1']
        d2 = c_res['d2']

        st.markdown(f"## ⚔️ {s1_info['name']}  VS  {s2_info['name']}")

        r1 = d1.get('top_ratios', {})
        r2 = d2.get('top_ratios', {})
        all_metrics = list(set(r1.keys()).union(set(r2.keys())))

        comp_rows = []
        for m in all_metrics:
            comp_rows.append({
                'Financial Metric': m,
                s1_info['name']: r1.get(m, 'N/A'),
                s2_info['name']: r2.get(m, 'N/A')
            })

        st.markdown("### 📊 Side-by-Side Financial Ratios Matrix")
        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True)

        st.markdown("---")
        st.markdown(f"### 🤖 Comparative AI Analysis & Horizon Winners")
        if c_res.get('error'):
            st.warning(f"⚠️ {c_res['error']}")
        st.info(f"⚙️ **Engine Provider Used:** `{c_res.get('provider_used', 'N/A')}`")
        st.markdown(c_res['report'])

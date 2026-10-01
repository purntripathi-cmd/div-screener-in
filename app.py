import os
import datetime
from zoneinfo import ZoneInfo
import streamlit as st
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(
    page_title="Institutional Dividend, REIT & InvIT Screener", 
    page_icon="🏢", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

IST = ZoneInfo("Asia/Kolkata")
INDIA_10Y_GSEC_BENCHMARK = 6.80  # 10Y Indian Sovereign Yield

# High-Density Institutional CSS
st.markdown("""
<style>
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 1.2rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 0.8rem !important;
    }
    .stSlider, .stSelectbox {
        margin-bottom: -8px !important;
    }
    h1 {
        font-size: 1.45rem !important;
        margin-bottom: 0.1rem !important;
        padding-bottom: 0rem !important;
    }
    p, span, label {
        font-size: 0.82rem !important;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.05);
        padding: 6px 12px !important;
        border-radius: 6px;
        border: 1px solid rgba(128, 128, 128, 0.15);
    }
    div[data-testid="stMetricLabel"] > p {
        font-size: 0.72rem !important;
        margin-bottom: 0px !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
    }
    div[data-testid="stDataFrame"] {
        font-size: 0.80rem !important;
    }
    .status-banner {
        padding: 6px 14px;
        border-radius: 6px;
        font-size: 0.80rem;
        margin-bottom: 10px;
        border: 1px solid rgba(16, 185, 129, 0.3);
        background-color: rgba(16, 185, 129, 0.08);
        color: inherit;
    }
    .conviction-card {
        padding: 10px 14px;
        border-radius: 8px;
        border: 1px solid rgba(16, 185, 129, 0.35);
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(59, 130, 246, 0.05) 100%);
        margin-bottom: 12px;
    }
    .card-title {
        font-size: 0.95rem;
        font-weight: 700;
        margin-bottom: 2px;
    }
    .card-sub {
        font-size: 0.78rem;
        color: #888888;
        margin-bottom: 6px;
    }
    .card-metric {
        font-size: 0.84rem;
        font-weight: 600;
    }
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# 15-Minute Auto-Refresh Meta Tag (Refreshes browser tab every 900 seconds)
st.markdown('<meta http-equiv="refresh" content="900">', unsafe_allow_html=True)

# Import Screener Data Engine
from screener_engine import (
    load_screener_cache, 
    fetch_live_screener_universe, 
    save_screener_cache,
    compute_screener_rankings,
    ASSET_UNIVERSE
)

# Load Data from Instant Cache
df, last_updated, feed_status = load_screener_cache()

# Header Section
h_left, h_right = st.columns([3.8, 1.4])
with h_left:
    st.title("⚡ Dynamic Dividend, REIT & InvIT Screener")
    st.caption(f"Ranked by Institutional Buy Suitability (Rank #1 = Most Preferred) • Benchmark: 10Y G-Sec ({INDIA_10Y_GSEC_BENCHMARK:.2f}%) • 15m Auto-Sync")

with h_right:
    st.write("")
    if st.button("🔄 Refresh Live Quotes", use_container_width=True):
        with st.spinner("Connecting to live exchange feeds..."):
            new_df, new_status = fetch_live_screener_universe()
            save_screener_cache(new_df, new_status)
            st.rerun()

# Telemetry Banner
st.markdown(
    f"""
    <div class="status-banner">
        ⏱️ <b>Auto-Refresh Engine: Active</b> (15-min background daemon + in-browser sync) &nbsp;|&nbsp; 
        🕒 <b>Last Data Update:</b> {last_updated} &nbsp;|&nbsp; 
        📡 <b>Feed Status:</b> {feed_status} &nbsp;|&nbsp;
        🎯 <b>Sorting:</b> Ranked by Buy Suitability (Rank 1 = Most Preferred)
    </div>
    """, 
    unsafe_allow_html=True
)

# Sidebar Filters
st.sidebar.markdown("### 🔍 Screener Filters")

asset_filter = st.sidebar.selectbox(
    "Asset Category", 
    ["All Assets", "REITs Only", "InvITs Only", "PSUs Only", "Private Equities Only"]
)

min_mcap, max_mcap = st.sidebar.slider(
    "Market Cap Range (₹ Cr)",
    min_value=0,
    max_value=2500000,
    value=(0, 2500000),
    step=5000,
    help="Filter by market capitalization in ₹ Crores"
)

min_div_yield = st.sidebar.slider("Min Yield (%)", 0.0, 16.0, 2.5, 0.25)
min_spread = st.sidebar.slider("Min Spread over G-Sec (bps)", -500, 800, -350, 25, help="Yield minus 10Y Sovereign Yield (6.80%) in basis points")
min_inst_hold = st.sidebar.slider("Min Institutional Holding (FII+DII %)", 0.0, 80.0, 10.0, 5.0)
min_promoter_hold = st.sidebar.slider("Min Promoter / Sponsor (%)", 0.0, 80.0, 0.0, 5.0)

st.sidebar.markdown("---")
max_de = st.sidebar.slider("Max Debt / Equity (Equities)", 0.0, 8.0, 4.5, 0.25)
tech_condition = st.sidebar.selectbox(
    "Technical Trend",
    ["All", "Above 200 EMA (Bullish)", "Above 50 EMA", "RSI Oversold (< 40)", "RSI Healthy (40 - 65)"]
)

# Data Filtering & Ranking Logic
if not df.empty:
    # Ensure ranking columns exist
    if "Rank" not in df.columns or "Buy Score" not in df.columns:
        df = compute_screener_rankings(df)

    filtered = df.copy()

    # Asset Classification Filter
    if asset_filter == "REITs Only":
        filtered = filtered[filtered["Type"] == "REIT"]
    elif asset_filter == "InvITs Only":
        filtered = filtered[filtered["Type"] == "InvIT"]
    elif asset_filter == "PSUs Only":
        filtered = filtered[filtered["Is_PSU"] == True]
    elif asset_filter == "Private Equities Only":
        filtered = filtered[(filtered["Type"] == "Equity") & (~filtered["Is_PSU"])]

    # Market Cap Range Filter
    filtered = filtered[(filtered["MCap (₹ Cr)"] >= min_mcap) & (filtered["MCap (₹ Cr)"] <= max_mcap)]

    # Yield & Spread Filters
    filtered = filtered[filtered["Yield (%)"] >= min_div_yield]
    filtered = filtered[filtered["G-Sec Spread (bps)"] >= min_spread]
    filtered = filtered[filtered["Inst (%)"] >= min_inst_hold]
    filtered = filtered[filtered["Promoter (%)"] >= min_promoter_hold]

    # Leverage Filter (exempt REITs/InvITs as asset debt is structurally regulated under SEBI caps)
    filtered = filtered[(filtered["Raw_DE"] <= max_de) | (filtered["Type"].isin(["REIT", "InvIT"]))]

    # Technical Condition
    if tech_condition == "Above 200 EMA (Bullish)":
        filtered = filtered[filtered["Above 200 EMA"] == True]
    elif tech_condition == "Above 50 EMA":
        filtered = filtered[filtered["Above 50 EMA"] == True]
    elif tech_condition == "RSI Oversold (< 40)":
        filtered = filtered[filtered["Raw_RSI"] < 40]
    elif tech_condition == "RSI Healthy (40 - 65)":
        filtered = filtered[(filtered["Raw_RSI"] >= 40) & (filtered["Raw_RSI"] <= 65)]

    # Sort strictly by Rank ascending (Rank 1 = Most Preferred at top)
    filtered = filtered.sort_values(by="Rank", ascending=True).reset_index(drop=True)

    # Key Summary Metrics
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Screened Assets", f"{len(filtered)} / {len(df)}")
    
    top_rank_1 = f"{filtered.iloc[0]['Ticker']} ({filtered.iloc[0]['Yield (%)']}%)" if not filtered.empty else "-"
    m2.metric("🥇 Rank 1 Asset", top_rank_1)

    top_rank_2 = f"{filtered.iloc[1]['Ticker']} ({filtered.iloc[1]['Yield (%)']}%)" if len(filtered) > 1 else "-"
    m3.metric("🥈 Rank 2 Asset", top_rank_2)

    m4.metric("Avg Screened Yield", f"{round(filtered['Yield (%)'].mean(), 2)}%" if not filtered.empty else "0%")
    m5.metric("Avg G-Sec Spread", f"{int(filtered['G-Sec Spread (bps)'].mean()):+d} bps" if not filtered.empty else "0 bps")
    m6.metric("Top Conviction (Rank 1-5)", f"{len(filtered[filtered['Rank'] <= 5])}" if not filtered.empty else "0")

    st.markdown("---")

    # Top 3 Conviction Buy Showcase Cards
    if len(filtered) >= 3:
        st.markdown("#### 🏆 Top Conviction Buy Recommendations (Most Preferred)")
        c_top1, c_top2, c_top3 = st.columns(3)
        top_cards = [
            (c_top1, filtered.iloc[0], "🥇 Rank 1 (Most Preferred)"),
            (c_top2, filtered.iloc[1], "🥈 Rank 2"),
            (c_top3, filtered.iloc[2], "🥉 Rank 3")
        ]
        for col, row, rank_title in top_cards:
            with col:
                st.markdown(
                    f"""
                    <div class="conviction-card">
                        <div class="card-title">{rank_title}: <b>{row['Ticker']}</b> ({row['Name']})</div>
                        <div class="card-sub">{row['Class']} • Sector: {row['Sector']}</div>
                        <div class="card-metric">
                            💰 <b>CMP:</b> ₹{row['CMP (₹)']} &nbsp;|&nbsp; 
                            📈 <b>Yield:</b> <span style="color:#10b981;">{row['Yield (%)']}%</span> &nbsp;|&nbsp; 
                            🎯 <b>Buy Score:</b> <b>{row['Buy Score']}/100</b>
                        </div>
                        <div style="font-size:0.75rem; margin-top:4px; color:#666;">
                            🏛️ <b>G-Sec Spread:</b> {row['G-Sec Spread (bps)']:+d} bps &nbsp;|&nbsp; 
                            🛡️ <b>Quality:</b> {row['Quality Score']}/100 &nbsp;|&nbsp;
                            🏷️ <b>Status:</b> {row['Suitability']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # Visual Analytics Tabs
    tab_grid, tab_charts, tab_methodology, tab_tax_guide, tab_daemon = st.tabs([
        "📋 Screener Table (Ranked)", 
        "📊 Yield & Risk Analytics", 
        "📐 Buy Ranking Methodology",
        "📑 Tax & SEBI NDCF Framework",
        "⚙️ Background 15-Min Auto-Sync"
    ])

    with tab_grid:
        display_cols = [
            "Rank_Badge", "Suitability", "Ticker", "Name", "Class", "Sector", "CMP (₹)", "Chg (%)",
            "Yield (%)", "G-Sec Spread (bps)", "Buy Score", "Quality Score", 
            "TTM DPU (₹)", "P/E", "P/B", "D/E", "Payout (%)", "Promoter (%)", "Inst (%)", 
            "RSI", "200 EMA", "From 52W H (%)", "MCap (₹ Cr)"
        ]

        # Rename Rank_Badge column to Rank for presentation
        df_display = filtered[display_cols].rename(columns={"Rank_Badge": "Rank"})

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            height=min(550, (len(filtered) + 1) * 35 + 10)
        )

        col_dl, col_info = st.columns([2, 5])
        with col_dl:
            st.download_button(
                "📥 Export Filtered List (CSV)",
                data=filtered[display_cols].to_csv(index=False).encode('utf-8'),
                file_name=f"ranked_dividend_screener_{datetime.datetime.now(IST).strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_info:
            st.caption("ℹ️ **Sorted by Rank (Rank 1 = Most Preferred Buy)**. Combines Sovereign Yield Spread advantage, Quality Score, 52W High margin of safety, payout sustainability, and technical trend.")

    with tab_charts:
        c_ch1, c_ch2 = st.columns(2)
        try:
            import plotly.express as px
            with c_ch1:
                fig_spread = px.bar(
                    filtered.head(15),
                    x="Ticker",
                    y="Buy Score",
                    color="Yield (%)",
                    color_continuous_scale="Viridis",
                    title="Top 15 Ranked Assets: Buy Conviction Score (0 - 100)",
                    hover_data=["Name", "Class", "Yield (%)", "CMP (₹)", "G-Sec Spread (bps)"]
                )
                fig_spread.update_layout(height=380, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_spread, use_container_width=True)

            with c_ch2:
                fig_scatter = px.scatter(
                    filtered,
                    x="From 52W H (%)",
                    y="Yield (%)",
                    size="Buy Score",
                    color="Type",
                    hover_name="Name",
                    title="Yield vs 52-Week High Discount (Bubble size = Buy Conviction Score)",
                    labels={"From 52W H (%)": "% from 52W High (Discount)", "Yield (%)": "Cash Yield (%)"}
                )
                fig_scatter.update_layout(height=380, margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(fig_scatter, use_container_width=True)
        except Exception:
            # Native Streamlit Fallback Charts
            with c_ch1:
                st.markdown("##### Buy Conviction Score (Top 15)")
                st.bar_chart(filtered.set_index("Ticker")["Buy Score"].head(15))
            with c_ch2:
                st.markdown("##### Distribution Yield (%) by Ticker")
                st.bar_chart(filtered.set_index("Ticker")["Yield (%)"].head(15))

    with tab_methodology:
        st.markdown(
            f"""
            #### 📐 Institutional Buy Suitability Ranking Methodology (Rank #1 = Most Preferred)
            
            Every asset in the screener is scored on a transparent **100-Point Quantitative Conviction Scale**:
            
            | Evaluation Pillar | Weight | Metric & Direction | Institutional Rationale |
            | :--- | :---: | :--- | :--- |
            | **1. Sovereign Spread Advantage** | **30%** | `Yield (%)` vs 10Y G-Sec ({INDIA_10Y_GSEC_BENCHMARK:.2f}%) *(Higher = Better)* | The fundamental rationale for owning yield assets is the risk premium over risk-free government debt. |
            | **2. Institutional Quality & Moat** | **25%** | `Quality Score (0-100)` *(Higher = Better)* | Evaluates Institutional (FII + DII) ownership depth, sovereign/sponsor pedigree (PSUs, NHAI, PowerGrid), and balance sheet safety. |
            | **3. Valuation Margin of Safety** | **20%** | `% Discount from 52W High` *(Higher Discount = Better)* | Accumulating high-yield assets at a pullback provides downside price protection and locks in higher yield on cost. |
            | **4. Distribution Sustainability** | **15%** | `Payout Ratio (%)` & `Debt/Equity` *(Moderate Payout + Low Leverage = Better)* | Statutory 90%+ NDCF pass-through for REITs/InvITs; prudent 30%–80% payout with D/E < 2.0 for equities. Avoids debt-funded dividend traps. |
            | **5. Technical Entry Zone** | **10%** | `RSI (14)` & `Moving Averages` *(Healthy Accumulation = Better)* | RSI in the 35–55 accumulation corridor with support near/above 50 & 200 EMAs. |
            
            ---
            
            ##### 🏷️ Buy Suitability Tiers
            - **🥇 Rank 1 to 5 (`🔥 Top Conviction Buy`)**: Premier risk-reward ratio, significant yield spread above sovereign bonds, backed by strong institutional sponsorship and sustainable cash distributions.
            - **Rank 6 to 12 (`🟢 Strong Accumulate`)**: High-quality aristocrats and trusts trading near fair value with dependable recurring cash payouts.
            - **Rank 13 to 22 (`🟡 Moderate Buy`)**: Quality dividend payers with moderate yield spread or cyclical price exposure.
            - **Rank 23+ (`⚪ Defensive / Hold`)**: Lower yield spread relative to sovereign bonds, higher leverage, or extended technical valuations.
            """
        )

    with tab_tax_guide:
        st.markdown(
            """
            #### 🏛️ Indian Taxation & Distribution Architecture for High-Yield Instruments
            
            | Asset Class | Cash Distribution Components | Taxation for Resident Unitholders / Shareholders |
            | :--- | :--- | :--- |
            | **Equities & PSUs** | 100% Dividend | Taxed at the investor's applicable **Income Tax Slab Rate**. TDS of 10% deducted if dividend > ₹5,000. |
            | **Real Estate Inv Trusts (REITs)** | • **Interest**: Pass-through<br>• **Dividend**: SPV tax status dependent<br>• **Return of Capital**: Sec 56(2)(xii) | • **Interest**: Taxed at investor's slab rate.<br>• **Dividend**: Tax-free if SPV chose Old Tax Regime; taxable if Concessional (Sec 115BAA).<br>• **Return of Capital**: Tax-exempt up to issue price; excess taxed as other income. |
            | **Infrastructure Inv Trusts (InvITs)** | • **Interest / SPV Debt Repayment**<br>• **Dividend** | Same pass-through status as REITs. Offers higher pre-tax cash yields (~9.5% - 12.5%) given long-term concession periods. |
            | **10Y Sovereign Benchmark** | Semi-annual Coupon (currently 6.80%) | Fully taxable at slab rate. Risk-free benchmark against which credit & equity risk premiums are evaluated. |
            """
        )

    with tab_daemon:
        st.markdown("#### ⚙️ Background 15-Minute Auto-Refresh Architecture")
        st.info(
            f"""
            **How auto-refresh works even when the app is closed:**
            1. **Autonomous Daemon (`screener_daemon.py`)**: Runs every 15 minutes (900 seconds) in the background.
            2. **Fast Batch Data Ingestion**: Uses multi-threaded batch queries to pull live quotes and technicals in under 5 seconds.
            3. **Resilient Local & Remote Sync**: Commits and pushes the fresh `screener_cache.json` snapshot to GitHub, ensuring Streamlit Cloud is always warm with zero cold-boot delays.
            4. **In-Browser Auto-Sync**: When you leave this web tab open, it also triggers a silent auto-refresh every 15 minutes.
            
            - **Current Interval:** 15 Minutes (900 seconds)
            - **Last Background Execution:** {last_updated}
            - **Benchmark Reference:** 10Y Indian G-Sec ({INDIA_10Y_GSEC_BENCHMARK:.2f}%)
            """
        )

else:
    st.error("Market data feeds are temporarily unreachable. Loading baseline dataset...")
    base_df = ASSET_UNIVERSE
    st.dataframe(pd.DataFrame(base_df))

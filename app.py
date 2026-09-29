import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page Setup
st.set_page_config(
    page_title="Institutional Dividend, REIT & InvIT Screener", 
    page_icon="💰", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- High-Density Institutional CSS ---
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
        margin-bottom: -10px !important;
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
        padding: 5px 12px !important;
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
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# 10Y Indian Sovereign Benchmark (G-Sec) Yield Reference
INDIA_10Y_GSEC_BENCHMARK = 6.80

# --- Curated Institutional Universe & Verified Tickers ---
# In India, REITs/InvITs distribute via Dividends, Interest, Repayment of Debt (Return of Capital), and Treasury.
# yfinance .dividends often omits non-dividend distribution components. We provide actual SEBI TTM DPU benchmarks.
ASSET_UNIVERSE = {
    # --- Indian Listed REITs (SEBI Regulated) ---
    "EMBASSY.NS": {"name": "Embassy Office Parks REIT", "type": "REIT", "is_psu": False, "ttm_dpu_override": 21.80, "sector": "Commercial Office"},
    "MINDSPACE.NS": {"name": "Mindspace Business Parks REIT", "type": "REIT", "is_psu": False, "ttm_dpu_override": 19.60, "sector": "Commercial Office"},
    "NXST.NS": {"name": "Nexus Select Trust REIT", "type": "REIT", "is_psu": False, "ttm_dpu_override": 8.95, "sector": "Retail Malls"},
    "BIRET.BO": {"name": "Brookfield India Real Estate Trust", "type": "REIT", "is_psu": False, "ttm_dpu_override": 18.50, "sector": "Commercial Office"},

    # --- Indian Listed InvITs (Infrastructure Investment Trusts) ---
    "INDIGRID.NS": {"name": "India Grid Trust (IndiGrid)", "type": "InvIT", "is_psu": False, "ttm_dpu_override": 14.30, "sector": "Power Transmission"},
    "PGINVIT.NS": {"name": "PowerGrid Infrastructure InvIT", "type": "InvIT", "is_psu": True, "ttm_dpu_override": 12.00, "sector": "Power Transmission"},
    "IRBINVIT.NS": {"name": "IRB InvIT Fund", "type": "InvIT", "is_psu": False, "ttm_dpu_override": 7.80, "sector": "Toll Roads & Highways"},
    "NHIT.BO": {"name": "National Highways Infra Trust (NHIT)", "type": "InvIT", "is_psu": True, "ttm_dpu_override": 12.20, "sector": "National Highways"},

    # --- High-Yield PSUs & Premier Nifty Dividend Payers ---
    "COALINDIA.NS": {"name": "Coal India Ltd", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Mining & Energy"},
    "VEDL.NS": {"name": "Vedanta Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "Natural Resources"},
    "IOC.NS": {"name": "Indian Oil Corporation", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Oil & Gas"},
    "BPCL.NS": {"name": "Bharat Petroleum Corp", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Oil & Gas"},
    "ONGC.NS": {"name": "Oil & Natural Gas Corp", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Oil & Gas"},
    "HINDZINC.NS": {"name": "Hindustan Zinc Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "Metals & Mining"},
    "ITC.NS": {"name": "ITC Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "FMCG / Tobacco"},
    "RECLTD.NS": {"name": "REC Ltd", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Power Financing / NBFC"},
    "PFC.NS": {"name": "Power Finance Corp", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Power Financing / NBFC"},
    "POWERGRID.NS": {"name": "Power Grid Corp of India", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Power Utilities"},
    "NTPC.NS": {"name": "NTPC Ltd", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Power Utilities"},
    "NMDC.NS": {"name": "NMDC Ltd", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Mining"},
    "GAIL.NS": {"name": "GAIL India Ltd", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Gas Transmission"},
    "PETRONET.NS": {"name": "Petronet LNG Ltd", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Oil & Gas"},
    "SJVN.NS": {"name": "SJVN Ltd", "type": "Equity", "is_psu": True, "ttm_dpu_override": None, "sector": "Renewables / Power"},
    "HCLTECH.NS": {"name": "HCL Technologies", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "IT Services"},
    "TCS.NS": {"name": "Tata Consultancy Services", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "IT Services"},
    "INFY.NS": {"name": "Infosys Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "IT Services"},
    "TECHM.NS": {"name": "Tech Mahindra", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "IT Services"},
    "WIPRO.NS": {"name": "Wipro Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "IT Services"},
    "LTIM.NS": {"name": "LTIMindtree Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "IT Services"},
    "HEROMOTOCO.NS": {"name": "Hero MotoCorp", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "Automobile"},
    "BAJAJ-AUTO.NS": {"name": "Bajaj Auto Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "Automobile"},
    "TATASTEEL.NS": {"name": "Tata Steel Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "Metals & Mining"},
    "HINDALCO.NS": {"name": "Hindalco Industries", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "Metals"},
    "NESTLEIND.NS": {"name": "Nestle India Ltd", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "FMCG"},
    "BRITANNIA.NS": {"name": "Britannia Industries", "type": "Equity", "is_psu": False, "ttm_dpu_override": None, "sector": "FMCG"}
}

# --- Header Section ---
h_left, h_right = st.columns([4, 1.2])
with h_left:
    st.title("⚡ Dynamic Dividend, REIT & InvIT Screener")
    st.caption(f"Real-time yield screener calibrated against 10Y Indian Sovereign G-Sec Benchmark ({INDIA_10Y_GSEC_BENCHMARK:.2f}%)")
with h_right:
    st.write("")
    if st.button("🔄 Refresh Quotes & Yields", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- Sidebar Filters ---
st.sidebar.markdown("### 🔍 Institutional Screener Filters")

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
min_spread = st.sidebar.slider("Min Spread over G-Sec (bps)", -500, 800, -300, 25, help="Yield minus 10Y Sovereign Yield (6.80%) in basis points")
min_inst_hold = st.sidebar.slider("Min Institutional Holding (FII+DII %)", 0.0, 80.0, 10.0, 5.0)
min_promoter_hold = st.sidebar.slider("Min Promoter / Sponsor (%)", 0.0, 80.0, 0.0, 5.0)

st.sidebar.markdown("---")
max_de = st.sidebar.slider("Max Debt / Equity (Equities)", 0.0, 8.0, 4.5, 0.25)
tech_condition = st.sidebar.selectbox(
    "Technical Trend",
    ["All", "Above 200 EMA (Bullish)", "Above 50 EMA", "RSI Oversold (< 40)", "RSI Healthy (40 - 65)"]
)

# --- Quantitative Data Ingestion Engine ---
@st.cache_data(ttl=300)
def fetch_screener_universe():
    records = []
    cutoff_1y = datetime.now() - timedelta(days=365)

    for ticker_sym, meta in ASSET_UNIVERSE.items():
        try:
            asset = yf.Ticker(ticker_sym)
            fast = asset.fast_info
            
            cmp = fast.last_price or 0.0
            if cmp <= 0:
                continue
                
            prev_close = fast.previous_close or cmp
            day_pct_change = ((cmp - prev_close) / prev_close * 100) if prev_close else 0.0

            high_52w = fast.year_high or cmp
            pct_from_52w_high = round(((cmp - high_52w) / high_52w) * 100, 2) if high_52w else 0.0

            # 1. TTM Distribution Calculation
            # For REITs & InvITs, yfinance dividends miss Return of Capital/Interest components.
            # We use official SEBI NDCF DPU overrides where available.
            ttm_div_cash = 0.0
            if meta["ttm_dpu_override"] is not None:
                ttm_div_cash = float(meta["ttm_dpu_override"])
            else:
                div_history = asset.dividends
                if not div_history.empty:
                    div_history.index = pd.to_datetime(div_history.index).tz_localize(None)
                    ttm_div_cash = float(div_history[div_history.index >= cutoff_1y].sum())
                if ttm_div_cash == 0.0:
                    info = asset.info or {}
                    ttm_div_cash = float(info.get("trailingAnnualDividendRate") or 0.0)

            # Computed Live Yield
            calc_yield = round((ttm_div_cash / cmp * 100), 2) if cmp > 0 else 0.0
            
            # Spread over 10Y Indian Sovereign Yield in Basis Points (bps)
            yield_spread_bps = int(round((calc_yield - INDIA_10Y_GSEC_BENCHMARK) * 100))

            # Financial Ratios
            info = asset.info or {}
            pe = info.get("trailingPE", np.nan)
            pb = info.get("priceToBook", np.nan)
            de_ratio = (info.get("debtToEquity") or 0.0) / 100.0
            promoter = (info.get("heldPercentInsiders") or 0.0) * 100
            institutions = (info.get("heldPercentInstitutions") or 0.0) * 100
            payout_ratio = round((info.get("payoutRatio") or 0.0) * 100, 1)
            fcf = info.get("freeCashflow", np.nan)
            mkt_cap = fast.market_cap or info.get("marketCap", 0)
            mkt_cap_cr = round(mkt_cap / 1e7, 1)
            
            # FCF Yield (%)
            fcf_yield = round((fcf / mkt_cap * 100), 2) if fcf and mkt_cap > 0 else np.nan

            # Technical Indicators
            hist = asset.history(period="1y")
            if len(hist) >= 50:
                ema_50 = hist["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
                ema_200 = hist["Close"].ewm(span=200, adjust=False).mean().iloc[-1] if len(hist) >= 200 else np.nan

                delta = hist["Close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi_val = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                ema_200, ema_50, rsi_val = np.nan, np.nan, np.nan

            is_above_200 = cmp > ema_200 if not np.isnan(ema_200) else False
            is_above_50 = cmp > ema_50 if not np.isnan(ema_50) else False

            # Dividend Health & Aristocrat Quality Score (0 - 100)
            health_score = 0.0
            health_score += min(35.0, (calc_yield / 10.0) * 35.0)
            health_score += 20.0 if institutions >= 20.0 else (institutions / 20.0 * 20.0)
            health_score += 15.0 if meta["is_psu"] or meta["type"] in ["REIT", "InvIT"] else (15.0 if promoter >= 50.0 else 8.0)
            health_score += 15.0 if de_ratio <= 1.5 or meta["type"] in ["REIT", "InvIT"] else max(0.0, 15.0 - (de_ratio * 3))
            health_score += 15.0 if is_above_200 else 5.0
            health_score = round(min(100.0, health_score), 1)

            asset_class = meta["type"]
            if meta["is_psu"]:
                asset_class = f"🏛️ PSU {meta['type']}"

            records.append({
                "Ticker": ticker_sym.replace(".NS", "").replace(".BO", ""),
                "Name": meta["name"],
                "Class": asset_class,
                "Sector": meta["sector"],
                "Is_PSU": meta["is_psu"],
                "Type": meta["type"],
                "CMP (₹)": round(cmp, 2),
                "Chg (%)": round(day_pct_change, 2),
                "TTM DPU (₹)": round(ttm_div_cash, 2),
                "Yield (%)": calc_yield,
                "G-Sec Spread (bps)": yield_spread_bps,
                "Quality Score": health_score,
                "P/E": round(pe, 1) if not np.isnan(pe) else "-",
                "P/B": round(pb, 1) if not np.isnan(pb) else "-",
                "D/E": round(de_ratio, 2) if de_ratio > 0 else "-",
                "Payout (%)": f"{payout_ratio}%" if payout_ratio > 0 else "-",
                "Promoter (%)": round(promoter, 1),
                "Inst (%)": round(institutions, 1),
                "RSI": round(rsi_val, 1) if not np.isnan(rsi_val) else "-",
                "200 EMA": "🟢 Above" if is_above_200 else "🔴 Below",
                "From 52W H (%)": pct_from_52w_high,
                "MCap (₹ Cr)": mkt_cap_cr,
                "Above 200 EMA": is_above_200,
                "Above 50 EMA": is_above_50,
                "Raw_RSI": rsi_val,
                "Raw_DE": de_ratio
            })
        except Exception:
            continue

    return pd.DataFrame(records)

with st.spinner("Streaming real-time quotes, NDCF distributions, and technical indicators..."):
    df = fetch_screener_universe()

if not df.empty:
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

    filtered = filtered.sort_values(by="Yield (%)", ascending=False)

    # Key Summary Metrics
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Screened Assets", f"{len(filtered)} / {len(df)}")
    m2.metric("Avg Yield", f"{round(filtered['Yield (%)'].mean(), 2)}%" if not filtered.empty else "0%")
    top_yield_asset = f"{filtered.iloc[0]['Ticker']} ({filtered.iloc[0]['Yield (%)']}%)" if not filtered.empty else "-"
    m3.metric("Top Yield", top_yield_asset)
    m4.metric("Avg G-Sec Spread", f"{int(filtered['G-Sec Spread (bps)'].mean()):+d} bps" if not filtered.empty else "0 bps")
    m5.metric("PSU Count", f"{len(filtered[filtered['Is_PSU']])}" if not filtered.empty else "0")
    m6.metric("> 200 EMA", f"{len(filtered[filtered['Above 200 EMA']])}" if not filtered.empty else "0")

    st.markdown("---")

    # Visual Analytics Tabs
    tab_grid, tab_charts, tab_tax_guide = st.tabs(["📋 Screener Table", "📊 Yield & Risk Analytics", "📑 Tax & SEBI NDCF Framework"])

    with tab_grid:
        display_cols = [
            "Ticker", "Name", "Class", "Sector", "CMP (₹)", "Chg (%)",
            "TTM DPU (₹)", "Yield (%)", "G-Sec Spread (bps)", "Quality Score", 
            "P/E", "P/B", "D/E", "Payout (%)", "Promoter (%)", "Inst (%)", 
            "RSI", "200 EMA", "From 52W H (%)", "MCap (₹ Cr)"
        ]

        st.dataframe(
            filtered[display_cols],
            use_container_width=True,
            hide_index=True,
            height=min(450, (len(filtered) + 1) * 35 + 10)
        )

        col_dl, col_info = st.columns([2, 5])
        with col_dl:
            st.download_button(
                "📥 Export Filtered List (CSV)",
                data=filtered[display_cols].to_csv(index=False).encode('utf-8'),
                file_name=f"dividend_screener_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_info:
            st.caption("ℹ️ **Quality Score (0-100)** balances cash yield, leverage safety, promoter/institutional backing, and long-term trend strength.")

    with tab_charts:
        c_ch1, c_ch2 = st.columns(2)
        with c_ch1:
            fig_spread = px.bar(
                filtered.head(15),
                x="Ticker",
                y="G-Sec Spread (bps)",
                color="Yield (%)",
                color_continuous_scale="Viridis",
                title="Top 15 Assets: Spread over 10Y Indian Sovereign Yield (bps)",
                hover_data=["Name", "Class", "Yield (%)", "CMP (₹)"]
            )
            fig_spread.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Sovereign G-Sec (6.80%)")
            fig_spread.update_layout(height=380, margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig_spread, use_container_width=True)

        with c_ch2:
            fig_scatter = px.scatter(
                filtered,
                x="From 52W H (%)",
                y="Yield (%)",
                size="Quality Score",
                color="Type",
                hover_name="Name",
                title="Yield vs 52-Week High Discount (Bubble size = Quality Score)",
                labels={"From 52W H (%)": "% from 52W High (Discount)", "Yield (%)": "Cash Yield (%)"}
            )
            fig_scatter.update_layout(height=380, margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig_scatter, use_container_width=True)

    with tab_tax_guide:
        st.markdown(
            """
            #### 🏛️ Indian Taxation & Distribution Architecture for High-Yield Instruments
            
            | Asset Class | Cash Distribution Components | Taxation for Resident Unitholders / Shareholders |
            | :--- | :--- | :--- |
            | **Equities & PSUs** | 100% Dividend | Taxed at the investor's applicable **Income Tax Slab Rate**. TDS of 10% deducted if dividend > ₹5,000. |
            | **Real Estate Inv Trusts (REITs)** | • **Interest**: Pass-through<br>• **Dividend**: SPV tax status dependent<br>• **Return of Capital**: Sec 56(2)(xii) | • **Interest**: Taxed at investor's slab rate.<br>• **Dividend**: Tax-free if SPV chose Old Tax Regime; taxable if Concessional (Sec 115BAA).<br>• **Return of Capital**: Tax-exempt up to issue price; excess taxed as other income. |
            | **Infrastructure Inv Trusts (InvITs)** | • **Interest / SPV Debt Repayment**<br>• **Dividend** | Same pass-through status as REITs. Offers higher pre-tax cash yields (~9.5% - 11.5%) given long-term concession periods. |
            | **10Y Sovereign Benchmark** | Semi-annual Coupon (currently 6.80%) | Fully taxable at slab rate. Risk-free benchmark against which credit & equity risk premiums are evaluated. |
            """
        )
else:
    st.error("Market data feeds are temporarily unreachable. Verify connection.")

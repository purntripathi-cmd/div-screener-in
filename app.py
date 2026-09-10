import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Page Setup
st.set_page_config(page_title="High-Yield Screener: REITs, InvITs & Nifty Dividends", layout="wide", initial_sidebar_state="expanded")

# --- Compact CSS: Minimize padding, compress typography, optimize whitespace ---
st.markdown("""
<style>
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.8rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 0.8rem !important;
    }
    .stSlider, .stSelectbox {
        margin-bottom: -12px !important;
    }
    h1 {
        font-size: 1.4rem !important;
        margin-bottom: 0.1rem !important;
        padding-bottom: 0rem !important;
    }
    p, span, label {
        font-size: 0.82rem !important;
    }
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.06);
        padding: 4px 10px !important;
        border-radius: 5px;
        border: 1px solid rgba(128, 128, 128, 0.15);
    }
    div[data-testid="stMetricLabel"] > p {
        font-size: 0.72rem !important;
        margin-bottom: 0px !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 1.1rem !important;
    }
    div[data-testid="stDataFrame"] {
        font-size: 0.78rem !important;
    }
    hr {
        margin-top: 0.4rem !important;
        margin-bottom: 0.4rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Dynamic Dividend, REIT & InvIT Screener")

# --- Comprehensive Asset Universe ---
# Includes Indian REITs, InvITs (from prompt/image), and Premier Dividend Equities (PSUs & Nifty Top Payers)
TICKER_CONFIG = {
    # --- REITs (from image) ---
    "EMBASSY.NS": {"name": "Embassy Office Parks REIT", "type": "REIT", "is_psu": False},
    "MINDSPACE.BO": {"name": "Mindspace Business Parks REIT", "type": "REIT", "is_psu": False},
    "NXST.NS": {"name": "Nexus Select Trust REIT", "type": "REIT", "is_psu": False},
    "BIRET.BO": {"name": "Brookfield India Real Estate Trust", "type": "REIT", "is_psu": False},
    "BAGMANE.BO": {"name": "Bagmane Prime Office REIT", "type": "REIT", "is_psu": False},

    # --- InvITs (from image) ---
    "INDIGRID.NS": {"name": "India Grid Trust (IndiGrid)", "type": "InvIT", "is_psu": False},
    "IRBINVIT.NS": {"name": "IRB InvIT Fund", "type": "InvIT", "is_psu": False},
    "PGINVIT.BO": {"name": "PowerGrid InvIT", "type": "InvIT", "is_psu": True},
    "CUBEINVIT.BO": {"name": "Cube Highways Trust", "type": "InvIT", "is_psu": False},
    "NHIT.BO": {"name": "National Highways Infra Trust (NHIT)", "type": "InvIT", "is_psu": True},

    # --- Nifty Dividend Equities & High-Yield PSUs ---
    "COALINDIA.NS": {"name": "Coal India Ltd", "type": "Equity", "is_psu": True},
    "VEDL.NS": {"name": "Vedanta Ltd", "type": "Equity", "is_psu": False},
    "IOC.NS": {"name": "Indian Oil Corp", "type": "Equity", "is_psu": True},
    "BPCL.NS": {"name": "Bharat Petroleum Corp", "type": "Equity", "is_psu": True},
    "ONGC.NS": {"name": "Oil & Natural Gas Corp", "type": "Equity", "is_psu": True},
    "HINDZINC.NS": {"name": "Hindustan Zinc Ltd", "type": "Equity", "is_psu": False},
    "ITC.NS": {"name": "ITC Ltd", "type": "Equity", "is_psu": False},
    "HCLTECH.NS": {"name": "HCL Technologies", "type": "Equity", "is_psu": False},
    "TCS.NS": {"name": "Tata Consultancy Services", "type": "Equity", "is_psu": False},
    "INFY.NS": {"name": "Infosys Ltd", "type": "Equity", "is_psu": False},
    "TECHM.NS": {"name": "Tech Mahindra", "type": "Equity", "is_psu": False},
    "WIPRO.NS": {"name": "Wipro Ltd", "type": "Equity", "is_psu": False},
    "LTIM.NS": {"name": "LTIMindtree Ltd", "type": "Equity", "is_psu": False},
    "RECLTD.NS": {"name": "REC Ltd", "type": "Equity", "is_psu": True},
    "PFC.NS": {"name": "Power Finance Corp", "type": "Equity", "is_psu": True},
    "POWERGRID.NS": {"name": "Power Grid Corp", "type": "Equity", "is_psu": True},
    "NTPC.NS": {"name": "NTPC Ltd", "type": "Equity", "is_psu": True},
    "NMDC.NS": {"name": "NMDC Ltd", "type": "Equity", "is_psu": True},
    "GAIL.NS": {"name": "GAIL India Ltd", "type": "Equity", "is_psu": True},
    "PETRONET.NS": {"name": "Petronet LNG", "type": "Equity", "is_psu": True},
    "HEROMOTOCO.NS": {"name": "Hero MotoCorp", "type": "Equity", "is_psu": False},
    "BAJAJ-AUTO.NS": {"name": "Bajaj Auto Ltd", "type": "Equity", "is_psu": False},
    "TATASTEEL.NS": {"name": "Tata Steel Ltd", "type": "Equity", "is_psu": False},
    "HINDALCO.NS": {"name": "Hindalco Industries", "type": "Equity", "is_psu": False},
    "NESTLEIND.NS": {"name": "Nestle India", "type": "Equity", "is_psu": False},
    "BRITANNIA.NS": {"name": "Britannia Industries", "type": "Equity", "is_psu": False},
    "SJVN.NS": {"name": "SJVN Ltd", "type": "Equity", "is_psu": True}
}

# --- Sidebar Filters ---
st.sidebar.markdown("### 🔍 Filter Criteria")

asset_filter = st.sidebar.selectbox(
    "Asset Category", 
    ["All", "REITs Only", "InvITs Only", "PSUs Only", "Private Equities Only"]
)

# Market Cap Filter
min_mcap, max_mcap = st.sidebar.slider(
    "Market Cap Range (₹ Cr)",
    min_value=0,
    max_value=2000000,
    value=(0, 2000000),
    step=5000,
    help="Filter assets based on total market capitalization in ₹ Crores"
)

min_div_yield = st.sidebar.slider("Min Yield (%)", 0.0, 16.0, 2.5, 0.25)
min_inst_hold = st.sidebar.slider("Min FII + DII (%)", 0.0, 80.0, 10.0, 5.0)
min_promoter_hold = st.sidebar.slider("Min Promoter / Sponsor (%)", 0.0, 80.0, 0.0, 5.0)

st.sidebar.markdown("---")
max_de = st.sidebar.slider("Max Debt/Equity", 0.0, 8.0, 5.0, 0.25)
tech_condition = st.sidebar.selectbox(
    "Technical Trend",
    ["All", "Above 200 EMA (Bullish)", "Above 50 EMA", "RSI Oversold (< 40)", "RSI Healthy (40 - 65)"]
)

# --- Data Fetching Engine ---
@st.cache_data(ttl=600)
def fetch_screener_universe():
    records = []
    cutoff_1y = datetime.now() - timedelta(days=365)

    for ticker_sym, meta in TICKER_CONFIG.items():
        try:
            asset = yf.Ticker(ticker_sym)
            fast = asset.fast_info
            
            # Live CMP & Changes
            cmp = fast.last_price or 0.0
            if cmp <= 0:
                continue
                
            prev_close = fast.previous_close or cmp
            day_pct_change = ((cmp - prev_close) / prev_close * 100) if prev_close else 0.0

            # 52-Week High Calculation
            high_52w = fast.year_high or cmp
            pct_from_52w_high = round(((cmp - high_52w) / high_52w) * 100, 2) if high_52w else 0.0

            # Dynamic 365-day TTM Cash Dividend Yield Calculation against live CMP
            div_history = asset.dividends
            ttm_div_cash = 0.0
            if not div_history.empty:
                div_history.index = pd.to_datetime(div_history.index).tz_localize(None)
                ttm_div_cash = float(div_history[div_history.index >= cutoff_1y].sum())

            # Fallback for trusts reporting distributions as adjustments
            info = asset.info or {}
            if ttm_div_cash == 0.0:
                raw_d = info.get("trailingAnnualDividendRate") or 0.0
                ttm_div_cash = float(raw_d)

            # Computed Live Yield
            calc_yield = round((ttm_div_cash / cmp * 100), 2) if cmp > 0 else 0.0

            # Ratios and Financials
            pe = info.get("trailingPE", np.nan)
            pb = info.get("priceToBook", np.nan)
            de_ratio = (info.get("debtToEquity") or 0.0) / 100.0
            promoter = (info.get("heldPercentInsiders") or 0.0) * 100
            institutions = (info.get("heldPercentInstitutions") or 0.0) * 100
            mkt_cap_cr = round((fast.market_cap or info.get("marketCap", 0)) / 1e7, 1)

            # Technicals (200 EMA, 50 EMA, 14-day RSI)
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

            # Display category with PSU badge
            asset_class = meta["type"]
            if meta["is_psu"]:
                asset_class = f"🏛️ PSU {meta['type']}"

            records.append({
                "Ticker": ticker_sym.replace(".NS", "").replace(".BO", ""),
                "Name": meta["name"],
                "Class": asset_class,
                "Is_PSU": meta["is_psu"],
                "Type": meta["type"],
                "CMP (₹)": round(cmp, 2),
                "Chg (%)": round(day_pct_change, 2),
                "TTM Div (₹)": round(ttm_div_cash, 2),
                "Div Yield (%)": calc_yield,
                "P/E": round(pe, 1) if not np.isnan(pe) else "-",
                "P/B": round(pb, 1) if not np.isnan(pb) else "-",
                "D/E": round(de_ratio, 2) if de_ratio > 0 else "-",
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

with st.spinner("Streaming latest quotes, distribution data, and indicators..."):
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

    # Yield & Holding Filters
    filtered = filtered[filtered["Div Yield (%)"] >= min_div_yield]
    filtered = filtered[filtered["Inst (%)"] >= min_inst_hold]
    filtered = filtered[filtered["Promoter (%)"] >= min_promoter_hold]

    # Leverage Filter (exempt REITs/InvITs as debt is structurally inherent to infra asset models)
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

    # Default descending sort by dynamically calculated Dividend Yield
    filtered = filtered.sort_values(by="Div Yield (%)", ascending=False)

    # Compact Metrics Overview
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Screened Assets", f"{len(filtered)} / {len(df)}")
    m2.metric("Avg Yield", f"{round(filtered['Div Yield (%)'].mean(), 2)}%" if not filtered.empty else "0%")
    m3.metric("Top Yield", f"{filtered.iloc[0]['Ticker']} ({filtered.iloc[0]['Div Yield (%)']}%)" if not filtered.empty else "-")
    m4.metric("PSU Count", f"{len(filtered[filtered['Is_PSU']])}" if not filtered.empty else "0")
    m5.metric("> 200 EMA", f"{len(filtered[filtered['Above 200 EMA']])}" if not filtered.empty else "0")

    # Table Grid
    display_cols = [
        "Ticker", "Name", "Class", "CMP (₹)", "Chg (%)",
        "TTM Div (₹)", "Div Yield (%)", "P/E", "P/B", "D/E",
        "Promoter (%)", "Inst (%)", "RSI", "200 EMA", "MCap (₹ Cr)"
    ]

    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        height=min(450, (len(filtered) + 1) * 35 + 5)
    )

    # Export Download Button
    st.download_button(
        "📥 Download Filtered List (CSV)",
        data=filtered[display_cols].to_csv(index=False).encode('utf-8'),
        file_name="dividend_screener_output.csv",
        mime="text/csv"
    )
else:
    st.error("Market data feeds are temporarily unreachable. Verify connection.")

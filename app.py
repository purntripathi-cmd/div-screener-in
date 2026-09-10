import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Page Setup
st.set_page_config(page_title="Dividend & Yield Screener", layout="wide", initial_sidebar_state="expanded")

# --- Dense CSS: Shrink padding, compact font sizes, eliminate blank space ---
st.markdown("""
<style>
    /* Remove huge top whitespace */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }
    /* Compact Sidebar */
    section[data-testid="stSidebar"] > div {
        padding-top: 1rem !important;
    }
    .stSlider, .stSelectbox {
        margin-bottom: -10px !important;
    }
    /* Header compression */
    h1 {
        font-size: 1.5rem !important;
        margin-bottom: 0.2rem !important;
        padding-bottom: 0rem !important;
    }
    p, span, label {
        font-size: 0.85rem !important;
    }
    /* Metric Card Shrinking */
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.05);
        padding: 6px 12px !important;
        border-radius: 6px;
        border: 1px solid rgba(128, 128, 128, 0.15);
    }
    div[data-testid="stMetricLabel"] > p {
        font-size: 0.75rem !important;
        margin-bottom: 0px !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 1.15rem !important;
    }
    /* Dataframe table font density */
    div[data-testid="stDataFrame"] {
        font-size: 0.80rem !important;
    }
    hr {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Real-Time Dividend, REIT & InvIT Screener")

# Universe with PSU and Instrument Classifications
TICKER_CONFIG = {
    # REITs & InvITs
    "EMBASSY.NS": {"name": "Embassy Office Parks", "type": "REIT", "is_psu": False},
    "BIRET.BO": {"name": "Brookfield India Real Estate", "type": "REIT", "is_psu": False},
    "MINDSPACE.BO": {"name": "Mindspace Business Parks", "type": "REIT", "is_psu": False},
    "PGINVIT.BO": {"name": "PowerGrid InvIT", "type": "InvIT", "is_psu": True},
    "NEXUS.NS": {"name": "Nexus Select Trust", "type": "REIT", "is_psu": False},
    "IRB.NS": {"name": "IRB InvIT Fund", "type": "InvIT", "is_psu": False},

    # High Dividend Equities & PSUs
    "COALINDIA.NS": {"name": "Coal India", "type": "Equity", "is_psu": True},
    "VEDL.NS": {"name": "Vedanta Ltd", "type": "Equity", "is_psu": False},
    "IOC.NS": {"name": "Indian Oil Corp", "type": "Equity", "is_psu": True},
    "BPCL.NS": {"name": "Bharat Petroleum", "type": "Equity", "is_psu": True},
    "ONGC.NS": {"name": "ONGC", "type": "Equity", "is_psu": True},
    "ITC.NS": {"name": "ITC Ltd", "type": "Equity", "is_psu": False},
    "HCLTECH.NS": {"name": "HCL Technologies", "type": "Equity", "is_psu": False},
    "TCS.NS": {"name": "Tata Consultancy Services", "type": "Equity", "is_psu": False},
    "INFY.NS": {"name": "Infosys Ltd", "type": "Equity", "is_psu": False},
    "RECLTD.NS": {"name": "REC Ltd", "type": "Equity", "is_psu": True},
    "PFC.NS": {"name": "Power Finance Corp", "type": "Equity", "is_psu": True},
    "SJVN.NS": {"name": "SJVN Ltd", "type": "Equity", "is_psu": True},
    "PETRONET.NS": {"name": "Petronet LNG", "type": "Equity", "is_psu": True},
    "POWERGRID.NS": {"name": "Power Grid Corp", "type": "Equity", "is_psu": True},
    "NMDC.NS": {"name": "NMDC Ltd", "type": "Equity", "is_psu": True},
    "GAIL.NS": {"name": "GAIL India", "type": "Equity", "is_psu": True}
}

# --- Compact Sidebar Filters ---
st.sidebar.markdown("### 🔍 Filters")

asset_filter = st.sidebar.selectbox(
    "Asset Category", 
    ["All", "PSUs Only", "REITs & InvITs Only", "Private Equities Only"]
)
min_div_yield = st.sidebar.slider("Min Yield (%)", 0.0, 15.0, 3.0, 0.25)
min_inst_hold = st.sidebar.slider("Min FII + DII (%)", 0.0, 80.0, 15.0, 5.0)
min_promoter_hold = st.sidebar.slider("Min Promoter / Sponsor (%)", 0.0, 80.0, 0.0, 5.0)

st.sidebar.markdown("---")
max_de = st.sidebar.slider("Max Debt/Equity", 0.0, 6.0, 4.0, 0.25)
tech_condition = st.sidebar.selectbox(
    "Technicals",
    ["All", "Above 200 EMA (Bullish)", "Above 50 EMA", "RSI Oversold (< 40)", "RSI Healthy (40 - 65)"]
)

# --- Data Fetching Engine ---
@st.cache_data(ttl=600)  # 10-minute cache refresh
def fetch_screener_universe():
    records = []
    cutoff_1y = datetime.now() - timedelta(days=365)

    for ticker_sym, meta in TICKER_CONFIG.items():
        try:
            asset = yf.Ticker(ticker_sym)

            # 1. Live CMP & Day Change
            fast = asset.fast_info
            cmp = fast.last_price or 0.0
            prev_close = fast.previous_close or cmp
            day_pct_change = ((cmp - prev_close) / prev_close * 100) if prev_close else 0.0

            # 2. 52-Week High Range
            high_52w = fast.year_high or cmp
            pct_from_52w_high = round(((cmp - high_52w) / high_52w) * 100, 2) if high_52w else 0.0

            # 3. Dynamic TTM Dividend Yield calculated on Live CMP
            div_history = asset.dividends
            ttm_div_cash = 0.0
            if not div_history.empty:
                div_history.index = pd.to_datetime(div_history.index).tz_localize(None)
                ttm_div_cash = float(div_history[div_history.index >= cutoff_1y].sum())

            # Fallback if dividends series is empty from provider
            info = asset.info
            if ttm_div_cash == 0.0:
                raw_d = info.get("trailingAnnualDividendRate") or 0.0
                ttm_div_cash = float(raw_d)

            # Recalculate dynamic yield against CMP
            calc_yield = round((ttm_div_cash / cmp * 100), 2) if cmp > 0 else 0.0

            # 4. Fundamentals & Ratios
            pe = info.get("trailingPE", np.nan)
            pb = info.get("priceToBook", np.nan)
            de_ratio = (info.get("debtToEquity") or 0.0) / 100.0
            promoter = (info.get("heldPercentInsiders") or 0.0) * 100
            institutions = (info.get("heldPercentInstitutions") or 0.0) * 100
            mkt_cap_cr = round((fast.market_cap or info.get("marketCap", 0)) / 1e7, 1)

            # 5. Technical Indicators
            hist = asset.history(period="1y")
            if len(hist) >= 200:
                ema_200 = hist["Close"].ewm(span=200, adjust=False).mean().iloc[-1]
                ema_50 = hist["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
                delta = hist["Close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi_val = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                ema_200, ema_50, rsi_val = np.nan, np.nan, np.nan

            is_above_200 = cmp > ema_200 if not np.isnan(ema_200) else False
            is_above_50 = cmp > ema_50 if not np.isnan(ema_50) else False

            # Type Display with PSU badge
            asset_type_badge = meta["type"]
            if meta["is_psu"]:
                asset_type_badge = f"🏛️ PSU {meta['type']}"

            records.append({
                "Ticker": ticker_sym.replace(".NS", "").replace(".BO", ""),
                "Name": meta["name"],
                "Class": asset_type_badge,
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
                "MCap (Cr)": mkt_cap_cr,
                "Above 200 EMA": is_above_200,
                "Above 50 EMA": is_above_50,
                "Raw_RSI": rsi_val,
                "Raw_DE": de_ratio
            })
        except Exception:
            continue

    return pd.DataFrame(records)

with st.spinner("Fetching ticks & calculating yields..."):
    df = fetch_screener_universe()

if not df.empty:
    filtered = df.copy()

    # Asset category / PSU filter
    if asset_filter == "PSUs Only":
        filtered = filtered[filtered["Is_PSU"] == True]
    elif asset_filter == "REITs & InvITs Only":
        filtered = filtered[filtered["Type"].isin(["REIT", "InvIT"])]
    elif asset_filter == "Private Equities Only":
        filtered = filtered[(filtered["Type"] == "Equity") & (~filtered["Is_PSU"])]

    # Fundamental & Holding Filters
    filtered = filtered[filtered["Div Yield (%)"] >= min_div_yield]
    filtered = filtered[filtered["Inst (%)"] >= min_inst_hold]
    filtered = filtered[filtered["Promoter (%)"] >= min_promoter_hold]
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

    # --- Always Sort by Dividend Yield (Calculated) Descending ---
    filtered = filtered.sort_values(by="Div Yield (%)", ascending=False)

    # --- Compact Metrics Row ---
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Screened", f"{len(filtered)} / {len(df)}")
    m2.metric("Avg Yield", f"{round(filtered['Div Yield (%)'].mean(), 2)}%" if not filtered.empty else "0%")
    m3.metric("Top Yield", f"{filtered.iloc[0]['Ticker']} ({filtered.iloc[0]['Div Yield (%)']}%)" if not filtered.empty else "-")
    m4.metric("PSU Count", f"{len(filtered[filtered['Is_PSU']])}" if not filtered.empty else "0")
    m5.metric(">200 EMA", f"{len(filtered[filtered['Above 200 EMA']])}" if not filtered.empty else "0")

    # --- Display Table ---
    display_cols = [
        "Ticker", "Name", "Class", "CMP (₹)", "Chg (%)",
        "TTM Div (₹)", "Div Yield (%)", "P/E", "P/B", "D/E",
        "Promoter (%)", "Inst (%)", "RSI", "200 EMA", "MCap (Cr)"
    ]

    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        height=min(400, (len(filtered) + 1) * 35 + 3)
    )

    # Minimalist download action
    st.download_button(
        "📥 Export Results (CSV)",
        data=filtered[display_cols].to_csv(index=False).encode('utf-8'),
        file_name="dividend_screener_output.csv",
        mime="text/csv"
    )
else:
    st.error("Market data feeds are temporarily unreachable.")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Dividend, REIT & InvIT Screener", layout="wide")
st.title("📈 Real-Time Dividend, REIT & InvIT Screener")
st.caption("Tracking live market prices, distributions, institutional holdings, valuation, and technical trend strength.")

# Universe of REITs, InvITs, and Premier Dividend Equities
TICKER_CONFIG = {
    # REITs & InvITs (from your watchlist)
    "EMBASSY.NS": {"name": "Embassy Office Parks REIT", "type": "REIT"},
    "BIRET.BO": {"name": "Brookfield India Real Estate Trust", "type": "REIT"},
    "MINDSPACE.BO": {"name": "Mindspace Business Parks REIT", "type": "REIT"},
    "PGINVIT.BO": {"name": "PowerGrid InvIT", "type": "InvIT"},
    "NEXUS.NS": {"name": "Nexus Select Trust", "type": "REIT"},
    "IRB.NS": {"name": "IRB InvIT Fund", "type": "InvIT"},
    
    # High Dividend Equities & PSUs
    "COALINDIA.NS": {"name": "Coal India Ltd", "type": "Equity"},
    "VEDL.NS": {"name": "Vedanta Ltd", "type": "Equity"},
    "IOC.NS": {"name": "Indian Oil Corporation", "type": "Equity"},
    "BPCL.NS": {"name": "Bharat Petroleum Corp", "type": "Equity"},
    "ONGC.NS": {"name": "Oil & Natural Gas Corp", "type": "Equity"},
    "ITC.NS": {"name": "ITC Ltd", "type": "Equity"},
    "HCLTECH.NS": {"name": "HCL Technologies", "type": "Equity"},
    "TCS.NS": {"name": "Tata Consultancy Services", "type": "Equity"},
    "INFY.NS": {"name": "Infosys Ltd", "type": "Equity"},
    "RECLTD.NS": {"name": "REC Ltd", "type": "Equity"},
    "PFC.NS": {"name": "Power Finance Corp", "type": "Equity"},
    "SJVN.NS": {"name": "SJVN Ltd", "type": "Equity"},
    "PETRONET.NS": {"name": "Petronet LNG", "type": "Equity"},
    "POWERGRID.NS": {"name": "Power Grid Corp", "type": "Equity"}
}

# --- Sidebar Filters ---
st.sidebar.header("🔍 Screener Criteria")

asset_filter = st.sidebar.selectbox("Asset Category", ["All", "REITs & InvITs Only", "Equities Only"])
min_div_yield = st.sidebar.slider("Min Dividend / NDCF Yield (%)", 0.0, 15.0, 3.5, 0.25)
min_inst_hold = st.sidebar.slider("Min Institutional (FII + DII) Holding (%)", 0.0, 80.0, 15.0, 5.0)
min_promoter_hold = st.sidebar.slider("Min Promoter / Sponsor Holding (%)", 0.0, 80.0, 0.0, 5.0)

st.sidebar.markdown("---")
st.sidebar.subheader("Valuation & Technicals")
max_de = st.sidebar.slider("Max Debt-to-Equity Ratio", 0.0, 6.0, 3.5, 0.25)
tech_condition = st.sidebar.selectbox(
    "Technical Filter",
    ["All", "Above 200 EMA (Bullish)", "Above 50 EMA", "RSI Oversold (< 40)", "RSI Neutral/Healthy (40 - 65)"]
)

# --- Data Fetching Engine ---
@st.cache_data(ttl=900)  # Auto-refresh cache every 15 mins during market hours
def fetch_screener_universe():
    records = []
    cutoff_1y = datetime.now() - timedelta(days=365)
    
    for ticker_sym, meta in TICKER_CONFIG.items():
        try:
            asset = yf.Ticker(ticker_sym)
            
            # 1. Live Price & Day Change
            fast = asset.fast_info
            cmp = fast.last_price or 0.0
            prev_close = fast.previous_close or cmp
            day_change = cmp - prev_close
            day_pct_change = (day_change / prev_close * 100) if prev_close else 0.0
            
            # 2. 52-Week Range
            high_52w = fast.year_high or cmp
            low_52w = fast.year_low or cmp
            pct_from_52w_high = round(((cmp - high_52w) / high_52w) * 100, 2) if high_52w else 0.0

            # 3. True TTM Dividend / NDCF Yield
            # Calculate from actual cash payouts credited over the past 365 days
            div_history = asset.dividends
            if not div_history.empty:
                div_history.index = pd.to_datetime(div_history.index).tz_localize(None)
                ttm_divs = div_history[div_history.index >= cutoff_1y].sum()
                calc_yield = (ttm_divs / cmp * 100) if cmp > 0 else 0.0
            else:
                calc_yield = 0.0

            # Fallback to info yield if distribution data hasn't populated
            info = asset.info
            if calc_yield == 0.0:
                raw_yield = info.get("dividendYield") or info.get("trailingAnnualDividendYield") or 0.0
                calc_yield = raw_yield * 100 if raw_yield < 1.0 else raw_yield

            # 4. Fundamentals & Quality
            pe = info.get("trailingPE", np.nan)
            pb = info.get("priceToBook", np.nan)
            de_ratio = (info.get("debtToEquity") or 0.0) / 100.0
            promoter = (info.get("heldPercentInsiders") or 0.0) * 100
            institutions = (info.get("heldPercentInstitutions") or 0.0) * 100
            mkt_cap_cr = round((fast.market_cap or info.get("marketCap", 0)) / 1e7, 2)

            # 5. Technical Indicators (RSI & EMAs)
            hist = asset.history(period="1y")
            if len(hist) >= 200:
                ema_200 = hist["Close"].ewm(span=200, adjust=False).mean().iloc[-1]
                ema_50 = hist["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
                
                # RSI-14
                delta = hist["Close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi_val = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                ema_200, ema_50, rsi_val = np.nan, np.nan, np.nan

            records.append({
                "Ticker": ticker_sym.replace(".NS", "").replace(".BO", ""),
                "Name": meta["name"],
                "Type": meta["type"],
                "LTP (₹)": round(cmp, 2),
                "Change (₹)": round(day_change, 2),
                "Change (%)": round(day_pct_change, 2),
                "Div Yield (%)": round(calc_yield, 2),
                "P/E": round(pe, 1) if not np.isnan(pe) else "-",
                "P/B": round(pb, 2) if not np.isnan(pb) else "-",
                "D/E": round(de_ratio, 2) if de_ratio > 0 else "-",
                "Promoter (%)": round(promoter, 1),
                "Inst (FII+DII) (%)": round(institutions, 1),
                "RSI (14)": round(rsi_val, 1) if not np.isnan(rsi_val) else "-",
                "From 52W High (%)": pct_from_52w_high,
                "Above 200 EMA": cmp > ema_200 if not np.isnan(ema_200) else False,
                "Above 50 EMA": cmp > ema_50 if not np.isnan(ema_50) else False,
                "Raw_RSI": rsi_val,
                "Raw_DE": de_ratio,
                "Market Cap (₹ Cr)": mkt_cap_cr
            })
        except Exception:
            continue
            
    return pd.DataFrame(records)

with st.spinner("Fetching live tick feeds and distribution data..."):
    df = fetch_screener_universe()

if not df.empty:
    # --- Filter Pipeline ---
    filtered = df.copy()

    # Asset category
    if asset_filter == "REITs & InvITs Only":
        filtered = filtered[filtered["Type"].isin(["REIT", "InvIT"])]
    elif asset_filter == "Equities Only":
        filtered = filtered[filtered["Type"] == "Equity"]

    # Yield & Holding filters
    filtered = filtered[filtered["Div Yield (%)"] >= min_div_yield]
    filtered = filtered[filtered["Inst (FII+DII) (%)"] >= min_inst_hold]
    filtered = filtered[filtered["Promoter (%)"] >= min_promoter_hold]

    # Debt filter
    filtered = filtered[(filtered["Raw_DE"] <= max_de) | (filtered["Type"].isin(["REIT", "InvIT"]))]

    # Technical filter
    if tech_condition == "Above 200 EMA (Bullish)":
        filtered = filtered[filtered["Above 200 EMA"] == True]
    elif tech_condition == "Above 50 EMA":
        filtered = filtered[filtered["Above 50 EMA"] == True]
    elif tech_condition == "RSI Oversold (< 40)":
        filtered = filtered[filtered["Raw_RSI"] < 40]
    elif tech_condition == "RSI Neutral/Healthy (40 - 65)":
        filtered = filtered[(filtered["Raw_RSI"] >= 40) & (filtered["Raw_RSI"] <= 65)]

    # --- Metrics Bar ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Assets Matching", len(filtered), f"Out of {len(df)}")
    m2.metric("Avg Yield", f"{round(filtered['Div Yield (%)'].mean(), 2)}%" if not filtered.empty else "0%")
    m3.metric("Top Yield Asset", filtered.sort_values(by="Div Yield (%)", ascending=False).iloc[0]["Name"] if not filtered.empty else "-")
    m4.metric("Bullish (>200 EMA)", f"{len(filtered[filtered['Above 200 EMA']])}" if not filtered.empty else "0")

    # --- Table Display ---
    columns_order = [
        "Ticker", "Name", "Type", "LTP (₹)", "Change (%)", 
        "Div Yield (%)", "P/B", "P/E", "D/E", "Inst (FII+DII) (%)", 
        "RSI (14)", "From 52W High (%)", "Market Cap (₹ Cr)"
    ]

    st.dataframe(
        filtered[columns_order].sort_values(by="Div Yield (%)", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    # Download filtered results as CSV
    csv_data = filtered[columns_order].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Filtered List (CSV)", csv_data, "dividend_screener_results.csv", "text/csv")
else:
    st.error("Market data feed unavailable. Check network configuration.")

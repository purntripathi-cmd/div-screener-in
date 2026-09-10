import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="High Dividend & Yield Screener", layout="wide")
st.title("📊 Indian Dividend, REIT & InvIT Screener")
st.caption("Filters by Dividend Yield, Shareholding Quality, Fundamentals, and Technical Trend")

# Curated Universe: Top Dividend Equities, REITs, and InvITs (NSE tickers)
UNIVERSE = {
    # REITs & InvITs
    "EMBASSY.NS": "Embassy Office Parks REIT",
    "MINDSPACE.NS": "Mindspace Business Parks REIT",
    "BIRET.NS": "Brookfield India Real Estate Trust",
    "NEXUS.NS": "Nexus Select Trust",
    "POWERGRID.NS": "Power Grid Corporation",
    "PGINVIT.NS": "PGInvIT",
    "IRB.NS": "IRB InvIT Fund",
    
    # High-Yield Dividend Equities (PSU, FMCG, Tech, Commodities)
    "VEDL.NS": "Vedanta Ltd",
    "COALINDIA.NS": "Coal India",
    "IOC.NS": "Indian Oil Corp",
    "BPCL.NS": "Bharat Petroleum",
    "ONGC.NS": "ONGC",
    "ITC.NS": "ITC Ltd",
    "HCLTECH.NS": "HCL Technologies",
    "INFY.NS": "Infosys",
    "TCS.NS": "TCS",
    "PETRONET.NS": "Petronet LNG",
    "RECLTD.NS": "REC Ltd",
    "PFC.NS": "Power Finance Corp",
    "SJVN.NS": "SJVN Ltd",
    "NMDC.NS": "NMDC Ltd"
}

# --- Sidebar Filters ---
st.sidebar.header("🎯 Filter Criteria")

min_div_yield = st.sidebar.slider("Min Dividend Yield (%)", 0.0, 12.0, 3.5, 0.25)
min_promoter_hold = st.sidebar.slider("Min Promoter Holding (%)", 0.0, 80.0, 40.0, 5.0)
min_inst_hold = st.sidebar.slider("Min Combined FII + DII Holding (%)", 0.0, 80.0, 20.0, 5.0)
max_pe = st.sidebar.slider("Max P/E Ratio (Equities only)", 5.0, 60.0, 30.0, 2.0)
tech_filter = st.sidebar.selectbox(
    "Technical Condition",
    ["None", "Above 200 EMA (Bullish)", "RSI Oversold (< 40)", "RSI Healthy (40 - 65)"]
)

# --- Data Fetching & Processing ---
@st.cache_data(ttl=3600)  # Cache results for 1 hour
def fetch_screener_data():
    records = []
    
    for ticker, name in UNIVERSE.items():
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Fundamentals
            cmp = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            div_yield = (info.get("dividendYield") or 0.0) * 100
            trailing_pe = info.get("trailingPE", np.nan)
            pb_ratio = info.get("priceToBook", np.nan)
            market_cap_cr = round((info.get("marketCap", 0) / 1e7), 2)
            
            # Shareholding Pattern
            promoter = (info.get("heldPercentInsiders") or 0.0) * 100
            institutions = (info.get("heldPercentInstitutions") or 0.0) * 100
            
            # Historical Technicals (1 Year)
            hist = stock.history(period="1y")
            if len(hist) >= 200:
                ema_200 = hist["Close"].ewm(span=200, adjust=False).mean().iloc[-1]
                
                # 14-day RSI Calculation
                delta = hist["Close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                ema_200 = np.nan
                rsi = np.nan
            
            is_above_200_ema = cmp > ema_200 if not np.isnan(ema_200) else False

            records.append({
                "Ticker": ticker,
                "Name": name,
                "Price (₹)": round(cmp, 2),
                "Div Yield (%)": round(div_yield, 2),
                "P/E": round(trailing_pe, 2) if not np.isnan(trailing_pe) else "N/A",
                "P/B": round(pb_ratio, 2) if not np.isnan(pb_ratio) else "N/A",
                "Promoter (%)": round(promoter, 2),
                "Inst (FII+DII) (%)": round(institutions, 2),
                "RSI (14)": round(rsi, 2) if not np.isnan(rsi) else np.nan,
                "Above 200 EMA": is_above_200_ema,
                "Market Cap (₹ Cr)": market_cap_cr,
                "Raw_PE": trailing_pe
            })
        except Exception:
            continue

    return pd.DataFrame(records)

with st.spinner("Fetching market fundamentals and live indicators..."):
    df = fetch_screener_data()

# --- Filtering Pipeline ---
if not df.empty:
    filtered_df = df[
        (df["Div Yield (%)"] >= min_div_yield) &
        (df["Inst (FII+DII) (%)"] >= min_inst_hold)
    ]
    
    # Conditional Promoter check (REITs/InvITs have sponsor holdings instead of traditional promoters)
    filtered_df = filtered_df[
        (filtered_df["Promoter (%)"] >= min_promoter_hold) | 
        (filtered_df["Ticker"].str.contains("REIT|INVIT|MINDSPACE|NEXUS|BIRET"))
    ]
    
    # Valuation Filter
    filtered_df = filtered_df[
        (filtered_df["Raw_PE"].isna()) | (filtered_df["Raw_PE"] <= max_pe)
    ]
    
    # Technical Filter
    if tech_filter == "Above 200 EMA (Bullish)":
        filtered_df = filtered_df[filtered_df["Above 200 EMA"] == True]
    elif tech_filter == "RSI Oversold (< 40)":
        filtered_df = filtered_df[filtered_df["RSI (14)"] < 40]
    elif tech_filter == "RSI Healthy (40 - 65)":
        filtered_df = filtered_df[(filtered_df["RSI (14)"] >= 40) & (filtered_df["RSI (14)"] <= 65)]

    # Display Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Universe Tracked", len(df))
    col2.metric("Screened Assets", len(filtered_df))
    col3.metric("Avg Yield of Selection", f"{round(filtered_df['Div Yield (%)'].mean(), 2)}%" if not filtered_df.empty else "0.0%")

    # Display Table
    cols_to_show = [
        "Ticker", "Name", "Price (₹)", "Div Yield (%)", 
        "P/E", "P/B", "Promoter (%)", "Inst (FII+DII) (%)", 
        "RSI (14)", "Above 200 EMA", "Market Cap (₹ Cr)"
    ]
    st.dataframe(
        filtered_df[cols_to_show].sort_values(by="Div Yield (%)", ascending=False),
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("No data retrieved. Verify network connectivity to Yahoo Finance.")

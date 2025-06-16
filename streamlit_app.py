import streamlit as st
import pandas as pd
import numpy as np

st.title("📈 Crypto Scalper Backtest – BTC & ETH (1m, interattivo)")

@st.cache_data
def load_data():
    btc = pd.read_csv("BTC_USDT_1m.csv", parse_dates=["timestamp"])
    eth = pd.read_csv("ETH_USDT_1m.csv", parse_dates=["timestamp"])
    return btc, eth

def compute_rsi(series, period=6):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def backtest(df, tp_pct, sl_pct, max_candles):
    df = df.copy()
    df["ma25"] = df["close"].rolling(window=25).mean()
    df["ma99"] = df["close"].rolling(window=99).mean()
    df["rsi6"] = compute_rsi(df["close"])
    df["vol_avg"] = df["volume"].rolling(window=20).mean()
    df["green_full"] = (df["close"] > df["open"]) & (
        (df["close"] - df["open"]) > (df["high"] - df["low"]) * 0.5
    )

    entries = []
    for i in range(100, len(df) - max_candles):
        entry_conditions = [
            df.loc[i, "rsi6"] > 30 and df["rsi6"].iloc[i - 5:i].min() < 30,
            df.loc[i, "green_full"],
            df.loc[i, "close"] > df.loc[i, "ma25"] or df.loc[i, "close"] > df.loc[i, "ma99"],
            df.loc[i, "volume"] > df.loc[i, "vol_avg"]
        ]
        if sum(entry_conditions) >= 3:
            entry_price = df.loc[i, "close"]
            take_profit = entry_price * (1 + tp_pct / 100)
            stop_loss = entry_price * (1 - sl_pct / 100)
            for j in range(i + 1, min(i + max_candles, len(df))):
                price = df.loc[j, "close"]
                if price >= take_profit:
                    entries.append((df.loc[i, "timestamp"], "TP", entry_price, price))
                    break
                elif price <= stop_loss:
                    entries.append((df.loc[i, "timestamp"], "SL", entry_price, price))
                    break
            else:
                entries.append((df.loc[i, "timestamp"], "EXP", entry_price, df.loc[i + max_candles, "close"]))

    return pd.DataFrame(entries, columns=["Entry Time", "Exit Type", "Entry Price", "Exit Price"])


# === PARAMETRI INTERATTIVI ===
st.sidebar.header("🔧 Parametri Strategia")
tp_pct = st.sidebar.slider("Take Profit (%)", 0.5, 5.0, 1.5, step=0.1)
sl_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 5.0, 2.0, step=0.1)
max_candles = st.sidebar.slider("Durata max trade (minuti)", 10, 90, 60, step=5)

btc_df, eth_df = load_data()

tab1, tab2 = st.tabs(["BTC/USDT", "ETH/USDT"])

with tab1:
    st.subheader(f"Backtest BTC/USDT (1m)")
    btc_results = backtest(btc_df, tp_pct, sl_pct, max_candles)
    st.write(btc_results)
    st.metric("TP %", f"{(btc_results['Exit Type'] == 'TP').mean() * 100:.1f}%")
    st.metric("SL %", f"{(btc_results['Exit Type'] == 'SL').mean() * 100:.1f}%")
    st.metric("Expired %", f"{(btc_results['Exit Type'] == 'EXP').mean() * 100:.1f}%")

with tab2:
    st.subheader(f"Backtest ETH/USDT (1m)")
    eth_results = backtest(eth_df, tp_pct, sl_pct, max_candles)
    st.write(eth_results)
    st.metric("TP %", f"{(eth_results['Exit Type'] == 'TP').mean() * 100:.1f}%")
    st.metric("SL %", f"{(eth_results['Exit Type'] == 'SL').mean() * 100:.1f}%")
    st.metric("Expired %", f"{(eth_results['Exit Type'] == 'EXP').mean() * 100:.1f}%")

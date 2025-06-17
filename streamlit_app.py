import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📈 Crypto Scalper Backtest – BTC & ETH (1m, con simulazione P&L)")

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

def backtest(df, tp_pct, sl_pct, max_candles, min_entry_flags, capital, risk_pct):
    df = df.copy()
    df["ma25"] = df["close"].rolling(window=25).mean()
    df["ma99"] = df["close"].rolling(window=99).mean()
    df["rsi6"] = compute_rsi(df["close"])
    df["vol_avg"] = df["volume"].rolling(window=20).mean()
    df["green_full"] = (df["close"] > df["open"]) & (
        (df["close"] - df["open"]) > (df["high"] - df["low"]) * 0.5
    )

    entries = []
    equity = [capital]
    current_equity = capital

    for i in range(100, len(df) - max_candles):
        entry_conditions = [
            df.loc[i, "rsi6"] > 30 and df["rsi6"].iloc[i - 5:i].min() < 30,
            df.loc[i, "green_full"],
            df.loc[i, "close"] > df.loc[i, "ma25"] or df.loc[i, "close"] > df.loc[i, "ma99"],
            df.loc[i, "volume"] > df.loc[i, "vol_avg"]
        ]
        if sum(entry_conditions) >= min_entry_flags:
            entry_price = df.loc[i, "close"]
            tp = entry_price * (1 + tp_pct / 100)
            sl = entry_price * (1 - sl_pct / 100)
            risk_amount = current_equity * (risk_pct / 100)
            position_size = risk_amount / abs(entry_price - sl)

            exit_type = "EXP"
            exit_price = df.loc[i + max_candles, "close"]

            for j in range(i + 1, min(i + max_candles, len(df))):
                price = df.loc[j, "close"]
                if price >= tp:
                    exit_type = "TP"
                    exit_price = price
                    break
                elif price <= sl:
                    exit_type = "SL"
                    exit_price = price
                    break

            pnl = (exit_price - entry_price) * position_size if exit_type != "SL" else -risk_amount
            current_equity += pnl
            equity.append(current_equity)

            entries.append((df.loc[i, "timestamp"], exit_type, entry_price, exit_price, pnl, current_equity))

    results = pd.DataFrame(entries, columns=["Entry Time", "Exit Type", "Entry Price", "Exit Price", "PnL", "Equity"])
    return results, equity

# === PARAMETRI INTERATTIVI ===
st.sidebar.header("🔧 Parametri Strategia")
tp_pct = st.sidebar.slider("Take Profit (%)", 0.5, 5.0, 1.5, step=0.1)
sl_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 5.0, 2.0, step=0.1)
max_candles = st.sidebar.slider("Durata max trade (minuti)", 10, 480, 60, step=5)
min_entry_flags = st.sidebar.slider("Filtri tecnici minimi per ingresso", 1, 4, 3)

st.sidebar.header("💰 Parametri Capitale")
initial_capital = st.sidebar.number_input("Capitale iniziale (USDT)", 100, 100000, 1000, step=100)
risk_pct = st.sidebar.slider("Rischio per trade (%)", 0.1, 5.0, 1.0, step=0.1)

btc_df, eth_df = load_data()

tab1, tab2 = st.tabs(["BTC/USDT", "ETH/USDT"])

with tab1:
    st.subheader("Backtest BTC/USDT")
    btc_results, btc_equity = backtest(btc_df, tp_pct, sl_pct, max_candles, min_entry_flags, initial_capital, risk_pct)
    st.write(btc_results)
    st.metric("TP %", f"{(btc_results['Exit Type'] == 'TP').mean() * 100:.1f}%")
    st.metric("SL %", f"{(btc_results['Exit Type'] == 'SL').mean() * 100:.1f}%")
    st.metric("Expired %", f"{(btc_results['Exit Type'] == 'EXP').mean() * 100:.1f}%")
    st.metric("Equity Finale", f"{btc_results['Equity'].iloc[-1]:.2f} USDT")
    
    st.line_chart(btc_results[["Equity"]].set_index(btc_results["Entry Time"]))

with tab2:
    st.subheader("Backtest ETH/USDT")
    eth_results, eth_equity = backtest(eth_df, tp_pct, sl_pct, max_candles, min_entry_flags, initial_capital, risk_pct)
    st.write(eth_results)
    st.metric("TP %", f"{(eth_results['Exit Type'] == 'TP').mean() * 100:.1f}%")
    st.metric("SL %", f"{(eth_results['Exit Type'] == 'SL').mean() * 100:.1f}%")
    st.metric("Expired %", f"{(eth_results['Exit Type'] == 'EXP').mean() * 100:.1f}%")
    st.metric("Equity Finale", f"{eth_results['Equity'].iloc[-1]:.2f} USDT")

    st.line_chart(eth_results[["Equity"]].set_index(eth_results["Entry Time"]))

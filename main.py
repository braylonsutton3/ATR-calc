from datetime import datetime, time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(page_title="MNQ ATR Calculator", page_icon="⚡", layout="wide")

SYMBOL = "MNQ=F"
CONTRACTS = 8
POINT_VALUE = 2.00
STOP_ATR_MULTIPLE = 0.75
TARGET_ATR_MULTIPLE = 2.25
MAX_RISK = 450.00
MIN_ATR = 0.00
MAX_ATR = MAX_RISK / (CONTRACTS * POINT_VALUE * STOP_ATR_MULTIPLE)
ET = ZoneInfo("America/New_York")


@st.cache_data(ttl=20, show_spinner=False)
def get_mnq_data() -> pd.DataFrame:
    df = yf.download(
        SYMBOL,
        period="7d",
        interval="1m",
        auto_adjust=False,
        progress=False,
        prepost=True,
        threads=False,
    )
    if df.empty:
        return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(ET)
    return df.sort_index()


def morning_bias(df: pd.DataFrame) -> str:
    """Bias from completed 1-minute MNQ bars labeled 09:30 through 09:58 ET only."""
    if df.empty:
        return "WAIT"

    today = datetime.now(ET).date()
    bars = df[
        (df.index.date == today)
        & (df.index.time >= time(9, 30))
        & (df.index.time <= time(9, 58))
    ].dropna(subset=["Open", "High", "Low", "Close", "Volume"])

    # Require nearly the whole completed window so partial/stale data cannot set bias.
    if len(bars) < 27 or bars.index[-1].time() < time(9, 58):
        return "WAIT"

    close = bars["Close"].astype(float)
    open_ = bars["Open"].astype(float)
    high = bars["High"].astype(float)
    low = bars["Low"].astype(float)
    volume = bars["Volume"].astype(float)

    typical = (high + low + close) / 3.0
    vwap = float((typical * volume).sum() / volume.sum()) if volume.sum() > 0 else float(typical.mean())
    slope = float(np.polyfit(np.arange(len(close), dtype=float), close.to_numpy(), 1)[0])
    net_move = float(close.iloc[-1] - open_.iloc[0])
    up_volume = float(volume.where(close > open_, 0.0).sum())
    down_volume = float(volume.where(close < open_, 0.0).sum())

    votes = [
        1 if net_move > 0 else -1 if net_move < 0 else 0,
        1 if close.iloc[-1] > vwap else -1 if close.iloc[-1] < vwap else 0,
        1 if slope > 0 else -1 if slope < 0 else 0,
        1 if up_volume > down_volume else -1 if down_volume > up_volume else 0,
        1 if (close.diff().dropna() > 0).sum() > (close.diff().dropna() < 0).sum() else -1,
    ]
    score = sum(votes)
    if score >= 3:
        return "LONG"
    if score <= -3:
        return "SHORT"
    return "WAIT"


def money(value: float, signed: bool = False) -> str:
    if signed:
        sign = "+" if value >= 0 else "−"
        return f"{sign}${abs(value):,.2f}"
    return f"${value:,.2f}"


st.markdown(
    """
    <style>
      .block-container {max-width: 1120px; padding-top: 1.3rem; padding-bottom: 1rem;}
      div[data-testid="stMetric"] {background:#111827; border:1px solid #263244; border-radius:14px; padding:14px;}
      div[data-testid="stMetricLabel"] {font-size:.82rem;}
      div[data-testid="stMetricValue"] {font-size:1.65rem;}
      .signal {text-align:center; padding:16px; border-radius:14px; font-size:2rem; font-weight:800; margin:.35rem 0 1rem;}
      .long {background:#063d2b; color:#5cffbd; border:1px solid #087b54;}
      .short {background:#4a171d; color:#ff8792; border:1px solid #94303b;}
      .wait {background:#3b3212; color:#ffe070; border:1px solid #78651c;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("MNQ ATR Calculator")
st.caption("8 contracts · $450 maximum risk · 0.75× ATR stop · 3R target")

try:
    market_data = get_mnq_data()
    bias = morning_bias(market_data)
except Exception:
    bias = "WAIT"

signal_class = {"LONG": "long", "SHORT": "short", "WAIT": "wait"}[bias]
st.markdown(f'<div class="signal {signal_class}">{bias}</div>', unsafe_allow_html=True)

top1, top2, top3 = st.columns(3)
top1.metric("Contracts", CONTRACTS)
top2.metric("Minimum ATR", f"{MIN_ATR:.2f}")
top3.metric("Maximum ATR", f"{MAX_ATR:.2f}")

atr = st.number_input(
    "Locked ATR(14) through 9:59",
    min_value=0.0,
    value=0.0,
    step=0.01,
    format="%.2f",
)

valid = MIN_ATR <= atr <= MAX_ATR and atr > 0 and bias in ("LONG", "SHORT")
stop_distance = STOP_ATR_MULTIPLE * atr
target_distance = TARGET_ATR_MULTIPLE * atr
risk = stop_distance * POINT_VALUE * CONTRACTS
reward = target_distance * POINT_VALUE * CONTRACTS
breakeven_trigger_dollars = risk

status = "TRADE" if valid else "WAIT"
st.subheader(status)

r1, r2, r3 = st.columns(3)
r1.metric("Take profit", money(reward, signed=True))
r2.metric("Stop loss", money(-risk, signed=True))
r3.metric("Move stop to breakeven at", money(breakeven_trigger_dollars, signed=True))

if atr > MAX_ATR:
    st.error(f"WAIT — ATR exceeds {MAX_ATR:.2f}; planned risk is above {money(MAX_RISK)}.")
elif bias == "WAIT":
    st.warning("WAIT")

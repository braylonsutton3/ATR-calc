import streamlit as st


# Dollars gained or lost from a 1.00-point move in one contract.
SYMBOLS = {
    "MNQ": {"name": "Micro E-mini Nasdaq-100", "point_value": 2.00},
    "MES": {"name": "Micro E-mini S&P 500", "point_value": 5.00},
    "MGC": {"name": "Micro Gold", "point_value": 10.00},
    "MYM": {"name": "Micro E-mini Dow", "point_value": 0.50},
    "M2K": {"name": "Micro E-mini Russell 2000", "point_value": 5.00},
    "MCL": {"name": "Micro WTI Crude Oil", "point_value": 100.00},
}

STOP_ATR_MULTIPLE = 0.75
TARGET_R_MULTIPLE = 3.0
MIN_MARKET_RISK = 30.0
MAX_TOTAL_LOSS = 450.0


st.set_page_config(page_title="Strategy 1 Dollar Calculator", page_icon="🧮")
st.title("Strategy 1 Dollar Risk Calculator")
st.caption("No live price is required · Stop = 0.75 ATR · Target = 3R")

symbol = st.selectbox("Micro futures symbol", list(SYMBOLS))
atr = st.number_input("Current ATR(14)", min_value=0.0, value=6.83, step=0.01, format="%.4f")
contracts = st.number_input("Number of contracts", min_value=1, value=3, step=1)
round_trip_cost = st.number_input(
    "Estimated total fees and commissions ($)", min_value=0.0, value=12.00, step=0.01
)

point_value = SYMBOLS[symbol]["point_value"]
stop_distance_points = atr * STOP_ATR_MULTIPLE

# These results work the same for LONG and SHORT market/limit entries.
market_risk = stop_distance_points * point_value * contracts
total_loss_if_stopped = market_risk + round_trip_cost
gross_profit_target = market_risk * TARGET_R_MULTIPLE
estimated_net_profit = gross_profit_target - round_trip_cost
breakeven_trigger_profit = market_risk

st.subheader("Amounts to enter")
c1, c2 = st.columns(2)
c1.metric("Stop-loss amount", f"${market_risk:,.2f}")
c2.metric("Take-profit amount", f"${gross_profit_target:,.2f}")

st.subheader("Additional information")
c1, c2, c3 = st.columns(3)
c1.metric("Loss including costs", f"${total_loss_if_stopped:,.2f}")
c2.metric("Estimated net at target", f"${estimated_net_profit:,.2f}")
c3.metric("Move stop to breakeven after", f"+${breakeven_trigger_profit:,.2f}")

st.write(f"**ATR stop distance:** {stop_distance_points:,.2f} points")
st.write(f"**Position value:** ${point_value * contracts:,.2f} per point")

if total_loss_if_stopped > MAX_TOTAL_LOSS:
    st.error(
        f"SKIP OR USE FEWER CONTRACTS: estimated loss including costs is above "
        f"the ${MAX_TOTAL_LOSS:.0f} Strategy 1 limit."
    )
elif market_risk < MIN_MARKET_RISK:
    st.warning(f"SKIP: market risk is below the ${MIN_MARKET_RISK:.0f} Strategy 1 minimum.")
else:
    st.success("Risk is inside the Strategy 1 range.")

st.info(
    "Use these dollar amounts with either a market or limit entry. No current market "
    "price is required. Actual loss can be larger during slippage, gaps, or fast markets."
)

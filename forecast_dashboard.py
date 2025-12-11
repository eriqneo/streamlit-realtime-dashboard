# forecast_dashboard.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import random
import math
from collections import deque

# ----------------------------
# Sales Event Generator (same as before)
# ----------------------------
CATEGORIES = {
    "Electronics": {"price_range": (80, 400), "weight": 0.30},
    "Apparel": {"price_range": (25, 120), "weight": 0.35},
    "Home & Garden": {"price_range": (40, 200), "weight": 0.20},
    "Beauty": {"price_range": (15, 90), "weight": 0.10},
    "Toys & Games": {"price_range": (20, 150), "weight": 0.05},
}

def generate_sales_event(base_hourly_revenue=30000, holiday_mode=False):
    t = time.time()
    hour = (int(t) // 3600) % 24
    peak_factor = 1.0 + 0.3 * math.sin((hour - 14) * math.pi / 12)
    if holiday_mode:
        peak_factor *= 2.0
    base_events_per_sec = base_hourly_revenue / 3600 / 100
    events_per_sec = base_events_per_sec * peak_factor
    num_orders = random.choices([1, 2, 3, 4], weights=[0.6, 0.25, 0.1, 0.05])[0]
    events = []
    for _ in range(num_orders):
        categories, weights = zip(*[(k, v["weight"]) for k, v in CATEGORIES.items()])
        category = random.choices(categories, weights=weights)[0]
        min_p, max_p = CATEGORIES[category]["price_range"]
        price = round(random.uniform(min_p, max_p), 2)
        events.append({"timestamp": t, "price": price})
    return events

# ----------------------------
# Forecasting Logic (stable version)
# ----------------------------
def aggregate_to_10s_bins(events, last_timestamp):
    if not events:
        return pd.Series([], dtype='float64')
    df = pd.DataFrame(events)
    df["time"] = pd.to_datetime(df["timestamp"], unit="s")
    df["bin"] = df["time"].dt.floor("10s")
    revenue_by_bin = df.groupby("bin")["price"].sum()
    end_bin = pd.Timestamp(last_timestamp).floor("10s")
    start_bin = end_bin - pd.Timedelta(minutes=10)
    full_index = pd.date_range(start=start_bin, end=end_bin, freq="10s")
    revenue_by_bin = revenue_by_bin.reindex(full_index, fill_value=0.0)
    return revenue_by_bin.sort_index()

def forecast_next_60s_simple(revenue_series):
    if len(revenue_series) < 6:
        return 0.0
    recent = revenue_series.tail(6)
    if recent.sum() == 0:
        return 0.0
    baseline = recent.mean()
    first_30s = recent.head(3).mean()
    last_30s = recent.tail(3).mean()
    trend = last_30s - first_30s if first_30s > 0 else 0
    pred_per_bin = max(0, baseline + trend / 2)
    return pred_per_bin * 6

# ----------------------------
# Initialize session state
# ----------------------------
if "events" not in st.session_state:
    st.session_state.events = deque(maxlen=1000)  # store raw events
if "forecasts" not in st.session_state:
    st.session_state.forecasts = []  # list of (timestamp, forecast_value)
if "last_forecast_time" not in st.session_state:
    st.session_state.last_forecast_time = 0
if "should_run" not in st.session_state:
    st.session_state.should_run = True

# ----------------------------
# Sidebar
# ----------------------------
st.sidebar.header("🔮 Forecast Controls")
revenue_target = st.sidebar.slider("Hourly Revenue ($K)", 10, 50, 30) * 1000
update_interval = st.sidebar.slider("Update Interval (sec)", 1, 10, 3)
holiday_mode = st.sidebar.checkbox("🎄 Holiday Mode", value=False)
forecast_every = st.sidebar.slider("Forecast Every (sec)", 20, 60, 30)

# ----------------------------
# Main UI
# ----------------------------
st.title("🔮 Live Sales Demand Forecast")
st.caption(f"Predicting next 60s of revenue • ~${revenue_target:,}/hour • Updates every {update_interval} sec")

col1, col2 = st.columns(2)
with col1:
    if st.button("⏸️ Pause"):
        st.session_state.should_run = False
with col2:
    if st.button("▶️ Resume"):
        st.session_state.should_run = True

# ----------------------------
# Generate events
# ----------------------------
if st.session_state.should_run:
    new_events = generate_sales_event(revenue_target, holiday_mode)
    st.session_state.events.extend(new_events)

# ----------------------------
# Forecast every N seconds
# ----------------------------
current_time = time.time()
if st.session_state.should_run and (current_time - st.session_state.last_forecast_time >= forecast_every):
    revenue_bins = aggregate_to_10s_bins(list(st.session_state.events), current_time)
    forecast_val = forecast_next_60s_simple(revenue_bins)
    st.session_state.forecasts.append((current_time, forecast_val))
    # Keep last 20 forecasts
    if len(st.session_state.forecasts) > 20:
        st.session_state.forecasts.pop(0)
    st.session_state.last_forecast_time = current_time

# ----------------------------
# Render dashboard
# ----------------------------
if st.session_state.events:
    # Compute last 60s actual
    df_events = pd.DataFrame(st.session_state.events)
    df_events["time"] = pd.to_datetime(df_events["timestamp"], unit="s")
    recent_60s = df_events[df_events["time"] > (pd.Timestamp.now() - pd.Timedelta(seconds=60))]
    last_60s_actual = recent_60s["price"].sum()
    
    # Get latest forecast
    latest_forecast = st.session_state.forecasts[-1][1] if st.session_state.forecasts else 0.0
    
    # MAPE (simplified: compare latest forecast to actual that followed)
    mape = abs(latest_forecast - last_60s_actual) / last_60s_actual * 100 if last_60s_actual > 0 else 0.0

    # Metrics
    st.subheader("📊 Forecast vs Actual (Last 60s)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Predicted Revenue", f"${latest_forecast:,.0f}")
    c2.metric("Actual Revenue", f"${last_60s_actual:,.0f}")
    c3.metric("Forecast Error", f"{mape:.1f}%")

    # Chart: show last 5 min of actual + latest forecast
    last_5_min = df_events[df_events["time"] > (pd.Timestamp.now() - pd.Timedelta(minutes=5))]
    if not last_5_min.empty:
        fig = go.Figure()
        # Actual revenue (binned)
        actual_bins = aggregate_to_10s_bins(list(st.session_state.events), time.time())
        actual_recent = actual_bins[actual_bins.index > (pd.Timestamp.now() - pd.Timedelta(minutes=5))]
        fig.add_trace(go.Scatter(
            x=actual_recent.index,
            y=actual_recent.values,
            mode='lines+markers',
            name='Actual',
            line=dict(color='#1f77b4')
        ))
        # Forecast (as a single point 60s ahead)
        if st.session_state.forecasts:
            forecast_time = pd.Timestamp(st.session_state.forecasts[-1][0]) + pd.Timedelta(seconds=60)
            fig.add_trace(go.Scatter(
                x=[forecast_time],
                y=[latest_forecast],
                mode='markers',
                name='Forecast',
                marker=dict(color='orange', size=10, symbol='star')
            ))
        fig.update_layout(
            title="Actual vs Forecast (Last 5 min)",
            xaxis_title="Time",
            yaxis_title="Revenue ($)",
            height=400,
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Raw events table (optional)
    st.subheader("📦 Recent Orders")
    display_df = df_events[["time", "price"]].tail(10).copy()
    display_df.columns = ["Time", "Revenue ($)"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("Initializing... waiting for first sales.")

# ----------------------------
# Auto-refresh
# ----------------------------
if st.session_state.should_run:
    time.sleep(update_interval)
    st.rerun()
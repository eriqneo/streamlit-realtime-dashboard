# sales_dashboard.py
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
import random
import math
from collections import deque

# ----------------------------
# Sales Event Generator
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
        peak_factor *= 2.0  # Double sales in holiday mode

    base_events_per_sec = base_hourly_revenue / 3600 / 100
    events_per_sec = base_events_per_sec * peak_factor
    num_orders = random.choices([1, 2, 3, 4], weights=[0.6, 0.25, 0.1, 0.05])[0]

    events = []
    for _ in range(num_orders):
        categories, weights = zip(*[(k, v["weight"]) for k, v in CATEGORIES.items()])
        category = random.choices(categories, weights=weights)[0]
        min_p, max_p = CATEGORIES[category]["price_range"]
        price = round(random.uniform(min_p, max_p), 2)
        traffic = max(50, int(events_per_sec * 3600 * random.uniform(0.8, 1.2)))
        events.append({
            "timestamp": t,
            "order_id": f"ord_{random.randint(10000, 99999)}",
            "product_category": category,
            "price": price,
            "traffic_this_min": traffic
        })
    return events

# ----------------------------
# Initialize session state
# ----------------------------
if "sales_events" not in st.session_state:
    st.session_state.sales_events = deque(maxlen=200)  # rolling buffer
if "should_run" not in st.session_state:
    st.session_state.should_run = True

# ----------------------------
# Sidebar Controls
# ----------------------------
st.sidebar.header("🛒 Sales Simulator")
revenue_target = st.sidebar.slider("Hourly Revenue Target ($K)", 10, 50, 30) * 1000
update_interval = st.sidebar.slider("Update Interval (sec)", 1, 10, 3)
holiday_mode = st.sidebar.checkbox("🎄 Holiday Mode (2x Sales)", value=False)

# ----------------------------
# Main UI
# ----------------------------
st.title("🛍️ Live Sales Performance Dashboard")
st.caption(f"Simulated e-commerce store • ~${revenue_target:,}/hour • Updates every {update_interval} sec")

col1, col2 = st.columns(2)
with col1:
    if st.button("⏸️ Pause"):
        st.session_state.should_run = False
with col2:
    if st.button("▶️ Resume"):
        st.session_state.should_run = True

# ----------------------------
# Generate & store events
# ----------------------------
if st.session_state.should_run:
    new_events = generate_sales_event(
        base_hourly_revenue=revenue_target,
        holiday_mode=holiday_mode
    )
    st.session_state.sales_events.extend(new_events)

# ----------------------------
# Compute Metrics (last 60 seconds of data)
# ----------------------------
if st.session_state.sales_events:
    df = pd.DataFrame(st.session_state.sales_events)
    df["time"] = pd.to_datetime(df["timestamp"], unit="s")
    
    # Filter to last 60 seconds for rate calculations
    now = pd.Timestamp.now()
    recent = df[df["time"] > (now - pd.Timedelta(seconds=60))]
    
    if not recent.empty:
        revenue_last_min = recent["price"].sum()
        orders_last_min = len(recent)
        aov = revenue_last_min / orders_last_min if orders_last_min > 0 else 0
        avg_traffic = recent["traffic_this_min"].mean()
        conversion_rate = (orders_last_min / avg_traffic * 100) if avg_traffic > 0 else 0
    else:
        revenue_last_min = orders_last_min = aov = conversion_rate = 0

    total_revenue = df["price"].sum()
    top_category = df["product_category"].mode().iloc[0] if not df.empty else "N/A"

    # Summary Metrics
    st.subheader("📈 Key Metrics (Last 60 sec)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Revenue", f"${revenue_last_min:,.0f}")
    m2.metric("Orders", f"{orders_last_min}")
    m3.metric("AOV", f"${aov:,.1f}")
    m4.metric("Conv. Rate", f"{conversion_rate:.1f}%")

    # Charts
    st.subheader("📊 Live Visualizations")

    # Revenue over time (last 5 min)
    last_5_min = df[df["time"] > (now - pd.Timedelta(minutes=5))]
    if not last_5_min.empty:
        fig1 = px.line(last_5_min, x="time", y="price", title="Revenue Stream (Last 5 min)")
        fig1.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    # Category breakdown
    cat_counts = df["product_category"].value_counts().head(5)
    fig2 = px.bar(
        x=cat_counts.values,
        y=cat_counts.index,
        orientation='h',
        title="Top Product Categories (All Time)",
        labels={"x": "Orders", "y": ""}
    )
    fig2.update_layout(height=300)
    st.plotly_chart(fig2, use_container_width=True)

    # Recent transactions table
    st.subheader("📦 Recent Orders")
    display_df = df[["time", "order_id", "product_category", "price"]].tail(10)
    display_df.columns = ["Time", "Order ID", "Category", "Price ($)"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("Initializing... waiting for first sales event.")

# ----------------------------
# Auto-refresh
# ----------------------------
if st.session_state.should_run:
    time.sleep(update_interval)
    st.rerun()
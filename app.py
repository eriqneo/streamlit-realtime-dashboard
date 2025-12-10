# app.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import time
import random
import math

# ----------------------------
# Data Generator (now accepts parameters)
# ----------------------------
def generate_data_point(base=50, trend_speed=0.02, noise_level=5, spike_prob=0.02):
    t = time.time()
    trend = base + 10 * math.sin(t * trend_speed) + 0.01 * t
    noise = random.gauss(0, noise_level)
    value = trend + noise
    if random.random() < spike_prob:
        value += random.uniform(20, 50)
    return {"timestamp": t, "value": round(value, 2)}

# ----------------------------
# Initialize session state
# ----------------------------
if "data" not in st.session_state:
    st.session_state.data = []
if "should_run" not in st.session_state:
    st.session_state.should_run = True

# ----------------------------
# SIDEBAR CONTROLS — ADD IT HERE!
# ----------------------------
st.sidebar.header("⚙️ Simulation Controls")
base = st.sidebar.slider("Base Activity", 10, 100, 50)
update_interval = st.sidebar.slider("Update Interval (sec)", 1, 10, 2)
noise = st.sidebar.slider("Noise Level", 0, 10, 5)
spike_prob = st.sidebar.slider("Spike Probability (%)", 0, 10, 2) / 100.0  # convert to 0.0–0.1

# ----------------------------
# Main UI
# ----------------------------
st.title("📊 Real-Time Streaming Analytics Dashboard")
st.caption(f"Live user activity • Updates every {update_interval} sec • Simulated data")

col1, col2 = st.columns(2)
with col1:
    if st.button("⏸️ Pause"):
        st.session_state.should_run = False
with col2:
    if st.button("▶️ Resume"):
        st.session_state.should_run = True

# ----------------------------
# Generate new data using SIDEBAR parameters
# ----------------------------
if st.session_state.should_run:
    new_point = generate_data_point(
        base=base,
        noise_level=noise,
        spike_prob=spike_prob
    )
    st.session_state.data.append(new_point)
    st.session_state.data = st.session_state.data[-100:]  # Keep last 100

# ----------------------------
# Render dashboard
# ----------------------------
if st.session_state.data:
    df = pd.DataFrame(st.session_state.data)
    df["time"] = pd.to_datetime(df["timestamp"], unit="s")
    
    current = df["value"].iloc[-1]
    peak = df["value"].max()
    low = df["value"].min()
    
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric("Current", f"{current:.1f}")
    metric_col2.metric("Peak", f"{peak:.1f}")
    metric_col3.metric("Low", f"{low:.1f}")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["value"],
        mode='lines+markers',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=4)
    ))
    fig.update_layout(
        title="Live User Activity Stream",
        xaxis_title="Time",
        yaxis_title="Events per Second",
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Initializing... first data point arriving shortly.")

# ----------------------------
# Auto-refresh using SIDEBAR interval
# ----------------------------
if st.session_state.should_run:
    time.sleep(update_interval)
    st.rerun()

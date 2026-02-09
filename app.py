import streamlit as st
import numpy as np
import plotly.graph_objects as go
import time
from config_params import (
    AREA_SIZE, SIM_TIME, DT, NUM_DRONES, DRONE_SPEED, DRONE_ALTITUDE,
    COVERAGE_RADIUS, SEARCH_RADIUS, BATTERY_INIT, TOWER_POSITION, STATION_POSITION,
    MAX_5G_RANGE, NUM_ISOLATED_VICTIMS, NUM_CLUSTER_ZONES, USERS_PER_CLUSTER,
    Drone, User, Tower, MonitoringStation, OperatorNotification,
    initialize_drones, initialize_users, update_simulation
)

# =============================================================================
# PAGE CONFIG & CUSTOM CSS
# =============================================================================
st.set_page_config(
    page_title="Drone Disaster Relief Dashboard",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium dark theme CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --bg-primary: #0f0f1a;
        --bg-secondary: #1a1a2e;
        --bg-card: rgba(30, 30, 50, 0.8);
        --accent-primary: #6366f1;
        --accent-secondary: #8b5cf6;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --border-color: rgba(99, 102, 241, 0.3);
    }
    
    .stApp {
        background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
        font-family: 'Inter', sans-serif;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(26, 26, 46, 0.95) 0%, rgba(15, 15, 26, 0.98) 100%);
        border-right: 1px solid var(--border-color);
    }
    
    [data-testid="stMetric"] {
        background: var(--bg-card);
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    [data-testid="stMetricLabel"] {
        color: var(--text-secondary) !important;
        font-size: 0.9rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }
    
    .main-title {
        background: linear-gradient(135deg, #6366f1, #8b5cf6, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .log-container {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 16px;
        max-height: 250px;
        overflow-y: auto;
    }
    
    .log-entry {
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        background: rgba(99, 102, 241, 0.1);
        border-left: 3px solid var(--accent-primary);
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SESSION STATE
# =============================================================================
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'current_time' not in st.session_state:
    st.session_state.current_time = 0
if 'drones' not in st.session_state:
    st.session_state.drones = None
if 'users' not in st.session_state:
    st.session_state.users = None
if 'tower' not in st.session_state:
    st.session_state.tower = None
if 'station' not in st.session_state:
    st.session_state.station = None
if 'operator' not in st.session_state:
    st.session_state.operator = None
if 'clusters_formed' not in st.session_state:
    st.session_state.clusters_formed = {}
if 'next_cluster_id' not in st.session_state:
    st.session_state.next_cluster_id = 0
if 'throughput_history' not in st.session_state:
    st.session_state.throughput_history = []
if 'detection_history' not in st.session_state:
    st.session_state.detection_history = []
if 'service_history' not in st.session_state:
    st.session_state.service_history = []

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def initialize_simulation():
    st.session_state.drones = initialize_drones()
    st.session_state.users = initialize_users()
    st.session_state.tower = Tower(TOWER_POSITION)
    st.session_state.station = MonitoringStation(STATION_POSITION)
    st.session_state.operator = OperatorNotification()
    st.session_state.clusters_formed = {}
    st.session_state.next_cluster_id = 0
    st.session_state.current_time = 0
    st.session_state.throughput_history = []
    st.session_state.detection_history = []
    st.session_state.service_history = []
    st.session_state.initialized = True

def run_simulation_steps(num_steps):
    """Run multiple simulation steps"""
    for _ in range(num_steps):
        if st.session_state.current_time >= SIM_TIME:
            break
            
        G, next_id = update_simulation(
            st.session_state.drones,
            st.session_state.users,
            st.session_state.tower,
            st.session_state.station,
            st.session_state.current_time,
            st.session_state.clusters_formed,
            st.session_state.next_cluster_id,
            st.session_state.operator
        )
        st.session_state.next_cluster_id = next_id
        st.session_state.current_time += DT
        
        users = st.session_state.users
        total_people = sum(u.group_size for u in users)
        detected_people = sum(u.group_size for u in users if u.detected)
        served_people = sum(u.group_size for u in users if u.served)
        total_thr = sum(u.throughput for u in users if u.served)
        
        st.session_state.throughput_history.append(total_thr)
        st.session_state.detection_history.append(detected_people / total_people * 100 if total_people > 0 else 0)
        st.session_state.service_history.append(served_people / total_people * 100 if total_people > 0 else 0)

def create_map_figure():
    fig = go.Figure()
    
    drones = st.session_state.drones
    users = st.session_state.users
    
    if drones is None or users is None:
        return fig
    
    alive_drones = [d for d in drones if d.alive]
    
    # Coverage circles
    for d in alive_drones:
        color = 'rgba(59, 130, 246, 0.12)' if d.mode == 'CLUSTER' else \
                'rgba(6, 182, 212, 0.12)' if d.mode == 'RELAY' else 'rgba(239, 68, 68, 0.10)'
        theta = np.linspace(0, 2*np.pi, 40)
        fig.add_trace(go.Scatter(
            x=d.pos[0] + COVERAGE_RADIUS * np.cos(theta),
            y=d.pos[1] + COVERAGE_RADIUS * np.sin(theta),
            fill='toself', fillcolor=color,
            line=dict(color='rgba(255,255,255,0.2)', width=1),
            hoverinfo='skip', showlegend=False
        ))
    
    # Tower range
    theta = np.linspace(0, 2*np.pi, 40)
    fig.add_trace(go.Scatter(
        x=TOWER_POSITION[0] + MAX_5G_RANGE * np.cos(theta),
        y=TOWER_POSITION[1] + MAX_5G_RANGE * np.sin(theta),
        mode='lines', line=dict(color='rgba(139, 92, 246, 0.25)', width=2, dash='dot'),
        name='5G Range', hoverinfo='skip'
    ))
    
    # Users
    undetected = [u for u in users if not u.detected]
    detected = [u for u in users if u.detected and not u.served]
    served = [u for u in users if u.served]
    
    if undetected:
        fig.add_trace(go.Scatter(
            x=[u.pos[0] for u in undetected], y=[u.pos[1] for u in undetected],
            mode='markers', marker=dict(size=[8 + u.group_size*2 for u in undetected],
                color='rgba(156, 163, 175, 0.6)', line=dict(color='white', width=1)),
            name=f'Undetected ({len(undetected)})'
        ))
    
    if detected:
        fig.add_trace(go.Scatter(
            x=[u.pos[0] for u in detected], y=[u.pos[1] for u in detected],
            mode='markers', marker=dict(size=[12 + u.group_size*2 for u in detected],
                color='#f59e0b', symbol='star', line=dict(color='white', width=1)),
            name=f'Detected ({len(detected)})'
        ))
    
    if served:
        fig.add_trace(go.Scatter(
            x=[u.pos[0] for u in served], y=[u.pos[1] for u in served],
            mode='markers', marker=dict(size=[14 + u.group_size*2 for u in served],
                color='#10b981', symbol='square', line=dict(color='white', width=1.5)),
            name=f'Served ({len(served)})'
        ))
    
    # Drones
    if alive_drones:
        colors = ['#3b82f6' if d.mode == 'CLUSTER' else '#06b6d4' if d.mode == 'RELAY' else '#ef4444' 
                  for d in alive_drones]
        fig.add_trace(go.Scatter(
            x=[d.pos[0] for d in alive_drones], y=[d.pos[1] for d in alive_drones],
            mode='markers+text',
            marker=dict(size=18, color=colors, symbol='triangle-up', line=dict(color='white', width=2)),
            text=[f'D{d.id}' for d in alive_drones], textposition='top center',
            textfont=dict(color='white', size=9), name='Drones'
        ))
    
    # Tower & Station
    fig.add_trace(go.Scatter(
        x=[TOWER_POSITION[0]], y=[TOWER_POSITION[1]], mode='markers',
        marker=dict(size=16, color='#8b5cf6', symbol='square', line=dict(color='white', width=2)),
        name='5G Tower'
    ))
    fig.add_trace(go.Scatter(
        x=[STATION_POSITION[0]], y=[STATION_POSITION[1]], mode='markers',
        marker=dict(size=16, color='#059669', symbol='diamond', line=dict(color='white', width=2)),
        name='Station'
    ))
    
    fig.update_layout(
        xaxis=dict(range=[0, AREA_SIZE], showgrid=True, gridcolor='rgba(255,255,255,0.1)',
                   zeroline=False, title='X (m)'),
        yaxis=dict(range=[0, AREA_SIZE], showgrid=True, gridcolor='rgba(255,255,255,0.1)',
                   zeroline=False, title='Y (m)', scaleanchor='x'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,15,26,0.8)',
        font=dict(color='#f1f5f9', family='Inter'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                   bgcolor='rgba(30,30,50,0.8)'),
        margin=dict(l=50, r=20, t=50, b=50), height=500
    )
    return fig

def create_charts():
    """Create combined throughput and progress charts"""
    fig = go.Figure()
    
    if st.session_state.throughput_history:
        fig.add_trace(go.Scatter(
            y=st.session_state.throughput_history, mode='lines',
            fill='tozeroy', fillcolor='rgba(99, 102, 241, 0.2)',
            line=dict(color='#6366f1', width=2), name='Throughput (Mbps)',
            yaxis='y1'
        ))
    
    if st.session_state.detection_history:
        fig.add_trace(go.Scatter(
            y=st.session_state.detection_history, mode='lines',
            line=dict(color='#f59e0b', width=2), name='Detected %', yaxis='y2'
        ))
        fig.add_trace(go.Scatter(
            y=st.session_state.service_history, mode='lines',
            line=dict(color='#10b981', width=2), name='Served %', yaxis='y2'
        ))
    
    fig.update_layout(
        title=dict(text='📈 Performance Metrics', font=dict(size=14)),
        xaxis=dict(title='Time Step', gridcolor='rgba(255,255,255,0.1)'),
        yaxis=dict(title='Throughput (Mbps)', gridcolor='rgba(255,255,255,0.1)', side='left'),
        yaxis2=dict(title='Percentage', overlaying='y', side='right', range=[0, 105]),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(15,15,26,0.8)',
        font=dict(color='#f1f5f9', family='Inter'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=280, margin=dict(l=60, r=60, t=50, b=40)
    )
    return fig

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.markdown("---")
    
    st.markdown("### 🚁 Drones")
    num_drones = st.slider("Count", 3, 20, NUM_DRONES)
    
    st.markdown("### 📡 Network")
    coverage_radius = st.slider("Coverage (m)", 50, 200, COVERAGE_RADIUS)
    
    st.markdown("### ⏱️ Simulation")
    sim_duration = st.slider("Duration (s)", 100, 1000, SIM_TIME, step=100)
    steps_per_click = st.slider("Steps per update", 5, 50, 20, 
                                help="More steps = faster but less smooth")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        step_btn = st.button("▶️ Step", use_container_width=True, 
                            help="Run simulation steps")
    with col2:
        reset_btn = st.button("🔄 Reset", use_container_width=True)
    
    run_all_btn = st.button("⏩ Run All", use_container_width=True,
                           help="Run simulation to completion")

# =============================================================================
# MAIN DASHBOARD
# =============================================================================
st.markdown('<h1 class="main-title">🚁 Drone Disaster Relief Dashboard</h1>', unsafe_allow_html=True)
st.markdown("*Real-time UAV network monitoring for disaster relief*")

# Handle buttons
if reset_btn or not st.session_state.initialized:
    initialize_simulation()

if step_btn and st.session_state.initialized:
    run_simulation_steps(steps_per_click)

if run_all_btn and st.session_state.initialized:
    remaining = int((sim_duration - st.session_state.current_time) / DT)
    run_simulation_steps(remaining)

# Progress
progress = st.session_state.current_time / sim_duration if sim_duration > 0 else 0
st.progress(min(progress, 1.0), text=f"⏱️ Time: {st.session_state.current_time:.0f}s / {sim_duration}s")

# KPIs
if st.session_state.drones and st.session_state.users:
    drones = st.session_state.drones
    users = st.session_state.users
    station = st.session_state.station
    
    alive_count = sum(1 for d in drones if d.alive)
    avg_battery = np.mean([d.battery for d in drones if d.alive]) if alive_count > 0 else 0
    battery_pct = (avg_battery / BATTERY_INIT) * 100
    
    total_people = sum(u.group_size for u in users)
    detected_people = sum(u.group_size for u in users if u.detected)
    served_people = sum(u.group_size for u in users if u.served)
    detection_rate = (detected_people / total_people * 100) if total_people > 0 else 0
    service_rate = (served_people / total_people * 100) if total_people > 0 else 0
    total_throughput = sum(u.throughput for u in users if u.served)
    report_count = len(station.received_reports) if station else 0
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("🚁 Drones", f"{alive_count}/{NUM_DRONES}")
    c2.metric("🔋 Battery", f"{battery_pct:.0f}%")
    c3.metric("👁️ Detected", f"{detection_rate:.1f}%")
    c4.metric("✅ Served", f"{service_rate:.1f}%")
    c5.metric("📶 Throughput", f"{total_throughput:.0f} Mbps")
    c6.metric("📋 Reports", f"{report_count}")

st.markdown("---")

# Map and Charts
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### 🗺️ Coverage Map")
    st.plotly_chart(create_map_figure(), use_container_width=True)

with col_right:
    st.plotly_chart(create_charts(), use_container_width=True)
    
    # Reports log
    st.markdown("### 📋 Reports")
    if st.session_state.station and st.session_state.station.received_reports:
        reports = st.session_state.station.received_reports[-8:][::-1]
        log_html = '<div class="log-container">'
        for r in reports:
            log_html += f'<div class="log-entry">t={r["time"]:.0f}s | D{r["drone_id"]} → {r["group_size"]}p | {r["hops"]}hop</div>'
        log_html += '</div>'
        st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.info("Click 'Step' to run simulation")

st.markdown("---")
st.caption("🚁 Drone Network Disaster Relief Simulation")

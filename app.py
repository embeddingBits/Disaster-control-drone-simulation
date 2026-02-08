import streamlit as st
import requests

st.set_page_config(layout="wide")
st.title("Drone Network Algorithm Explorer")

st.sidebar.header("Scenario Parameters")

num_drones = st.sidebar.slider("Number of Drones", 1, 40, 10)
num_users = st.sidebar.slider("Number of Users", 10, 200, 50)
coverage = st.sidebar.slider("Coverage Radius (m)", 50, 300, 120)
search = st.sidebar.slider("Search Radius (m)", 100, 500, 200)
sim_time = st.sidebar.slider("Simulation Time (steps)", 50, 500, 200)

if st.sidebar.button("Run Simulation"):
    payload = {
        "num_drones": num_drones,
        "num_users": num_users,
        "coverage_radius": coverage,
        "search_radius": search,
        "sim_time": sim_time
    }

    with st.spinner("Running simulation..."):
        res = requests.post("http://localhost:8000/run", json=payload).json()

    st.success("Simulation complete")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Detection %", f"{res['detection_rate']:.1f}%")
    col2.metric("Service %", f"{res['service_rate']:.1f}%")
    col3.metric("Avg Throughput", f"{res['avg_throughput']:.1f} Mbps")
    col4.metric("Alive Drones", res["alive_drones"])

    st.subheader("Network Throughput Over Time")
    st.line_chart(res["throughput_timeseries"])

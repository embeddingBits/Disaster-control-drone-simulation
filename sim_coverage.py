import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle
import networkx as nx

from config_params import *

# INITIALIZATION
print("\n" + "="*70)
print("2D NETWORK COVERAGE MAP SIMULATION")
print("="*70)
print(f"Simulation Duration: {SIM_TIME} seconds")
print(f"Number of Drones: {NUM_DRONES}")
print(f"Coverage Radius: {COVERAGE_RADIUS}m   Search Radius: {SEARCH_RADIUS}m")
print(f"Area: {AREA_SIZE} × {AREA_SIZE} m")
print("="*70 + "\n")

current_time = 0.0
operator = OperatorNotification()
tower   = Tower(TOWER_POSITION)
station = MonitoringStation(STATION_POSITION)
drones  = initialize_drones()
users   = initialize_users()
clusters_formed = {}
next_cluster_id = 0

# Create graph 
G = nx.DiGraph()

# VISUALIZATION SETUP
fig, ax = plt.subplots(figsize=(14, 12))
ax.set_xlim(0, AREA_SIZE)
ax.set_ylim(0, AREA_SIZE)
ax.set_xlabel("X (m)", fontsize=13)
ax.set_ylabel("Y (m)", fontsize=13)
ax.set_title("2D Drone Coverage & Multi-Hop Network Map", fontsize=16, fontweight='bold')
ax.set_aspect('equal')
ax.grid(True, alpha=0.3, linestyle='--')

status_text = fig.text(0.5, 0.015, "", ha='center', va='bottom', fontsize=11,
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='#e8f5e9', alpha=0.92))

link_lines = []

# ANIMATION UPDATE FUNCTION
def animate(frame):
    global current_time, next_cluster_id, G, link_lines

    current_time = frame * DT

    # Core simulation step 
    G, next_cluster_id = update_simulation(
        drones, users, tower, station, current_time,
        clusters_formed, next_cluster_id, operator
    )

    # Check for wave launch (same logic as 3D sim)
    operational_drones = [d for d in drones if d.alive and d.mode not in ["RETURNING", "LANDED"]]
    if len(operational_drones) <= NUM_DRONES * 0.5:
         num_to_launch = NUM_DRONES
         new_wave = station.launch_wave(num_to_launch)
         drones.extend(new_wave)

    alive_drones = [d for d in drones if d.alive]

    ax.clear()

    link_lines = []
    # Restore axes properties
    ax.set_xlim(0, AREA_SIZE)
    ax.set_ylim(0, AREA_SIZE)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title("2D Drone Coverage & Multi-Hop Network Map", fontsize=16, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')

    # Tower coverage background
    ax.add_patch(Circle(TOWER_POSITION[:2], MAX_5G_RANGE,
                        fc='purple', ec='purple', lw=1.5, ls='--', alpha=0.08))

    # Draw network links 
    for d in alive_drones:
        node = f'd{d.id}'
        if node in G:
            # Drone → Tower
            if G.has_edge(node, 'tower'):
                cap = G[node]['tower']['capacity']
                color = 'darkviolet' if cap > 70 else 'mediumpurple' if cap > 40 else 'plum'
                alpha = 0.75 if cap > 70 else 0.65
                lw = 2.8 if cap > 70 else 2.2
                line = ax.plot([d.pos[0], TOWER_POSITION[0]],
                               [d.pos[1], TOWER_POSITION[1]],
                               color=color, alpha=alpha, lw=lw, zorder=1)[0]
                link_lines.append(line)

            # Drone ↔ Drone 
            for d2 in alive_drones:
                if d.id < d2.id:
                    n2 = f'd{d2.id}'
                    if G.has_edge(node, n2):
                        cap = G[node][n2]['capacity']
                        color = 'green' if cap > 70 else 'orange' if cap > 40 else 'red'
                        alpha = 0.65 if cap > 70 else 0.55
                        lw = 1.9 if cap > 70 else 1.5
                        line = ax.plot([d.pos[0], d2.pos[0]],
                                       [d.pos[1], d2.pos[1]],
                                       color=color, alpha=alpha, lw=lw, zorder=1)[0]
                        link_lines.append(line)

    # Drone coverage circles
    for d in alive_drones:
        if d.mode == "RETURNING": color = 'orange'
        elif d.mode == "CLUSTER": color = 'blue'
        elif d.mode == "RELAY":   color = 'cyan'
        else:                     color = 'red'
        alpha_fill = 0.22 if d.mode == "CLUSTER" else 0.14
        ax.add_patch(Circle(d.pos[:2], COVERAGE_RADIUS, fc=color, ec=color, alpha=alpha_fill))
        ax.add_patch(Circle(d.pos[:2], SEARCH_RADIUS, fc='none', ec=color, alpha=0.35, ls=':', lw=1.1))

    # User → Drone serving lines 
    for u in users:
        if u.served and u.connected_drone is not None:
            drone = next((d for d in drones if d.id == u.connected_drone), None)
            if drone:
                hops = u.hops_to_tower or 99
                color = 'darkgreen' if hops <= 1 else 'limegreen' if hops == 2 else '#ffaa00'
                alpha = 0.6 - 0.15*max(0, hops-1)
                lw = 1.8 - 0.4*max(0, hops-1)
                ax.plot([u.pos[0], drone.pos[0]],
                        [u.pos[1], drone.pos[1]],
                        color=color, alpha=max(0.3, alpha), lw=lw, zorder=3)

    # Users by status
    undetected = [u for u in users if not u.detected]
    detected   = [u for u in users if u.detected and not u.served]
    served     = [u for u in users if u.served]

    # Status - Drone hasn't detected base; base hasn't recieved signal
    if undetected:
        ax.scatter([u.pos[0] for u in undetected], [u.pos[1] for u in undetected],
                   s=[28 + u.group_size*6 for u in undetected],
                   c='lightgray', edgecolor='k', alpha=0.75,
                   label=f'Undetected ({len(undetected)})')

    # Status - Drone has detected base; base hasn't recieved signal
    if detected:
        ax.scatter([u.pos[0] for u in detected], [u.pos[1] for u in detected],
                   s=[40 + u.group_size*6 for u in detected],
                   marker='*', c='orange', edgecolor='darkorange',
                   label=f'Detected ({len(detected)})')

    # Status - Drone has detected base; base has recieved signal
    if served:
        ax.scatter([u.pos[0] for u in served], [u.pos[1] for u in served],
                   s=[48 + u.group_size*6 for u in served],
                   marker='s', c='limegreen', edgecolor='darkgreen',
                   label=f'Served ({len(served)})')

    # Drones
    if alive_drones:
        colors = []
        for d in alive_drones:
            if d.mode == "RETURNING": colors.append('orange')
            elif d.mode == "CLUSTER": colors.append('blue')
            elif d.mode == "RELAY":   colors.append('cyan')
            else:                     colors.append('red')
        ax.scatter([d.pos[0] for d in alive_drones], [d.pos[1] for d in alive_drones],
                   c=colors, s=220, marker='^', edgecolor='black', lw=1.8, zorder=10)

        for d in alive_drones:
            pct = d.battery / BATTERY_INIT * 100
            col = 'green' if pct > 55 else 'orange' if pct > 25 else 'red'
            ax.text(d.pos[0], d.pos[1] + 28, f"D{d.id}\n{int(pct)}%",
                    ha='center', fontsize=8.5, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.35', fc='white', alpha=0.9, ec=col))

    # Tower & Station
    ax.scatter(*TOWER_POSITION[:2], s=100, marker='s', c='purple', edgecolor='black', lw=2.5,
               label='5G Tower', zorder=12)
    ax.scatter(*STATION_POSITION[:2], s=100, marker='D', c='darkgreen', edgecolor='black', lw=2.2,
               label='Monitoring Station', zorder=12)

    ax.legend(loc='upper right', fontsize=9.5, framealpha=0.95)

    # Status bar
    alive_cnt = len(alive_drones)
    det_p = sum(u.group_size for u in users if u.detected)
    srv_p = sum(u.group_size for u in users if u.served)
    tot_p = sum(u.group_size for u in users)
    tot_thr = sum(u.throughput for u in users if u.served)
    avg_bat = np.mean([d.battery for d in alive_drones]) if alive_drones else 0
    reports = len(station.received_reports)

    status_text.set_text(
        f"t = {current_time:.0f}s / {SIM_TIME}s   |   "
        f"Drones: {alive_cnt}/{NUM_DRONES}   |   "
        f"Battery avg: {avg_bat:.0f}J ({avg_bat/BATTERY_INIT*100:.0f}%)   |   "
        f"Detected: {det_p}/{tot_p}   |   "
        f"Served: {srv_p}/{tot_p} ({srv_p/tot_p*100:.1f}%)   |   "
        f"Throughput: {tot_thr:.1f} Mbps   |   "
        f"Clusters: {len(clusters_formed)}   |   "
        f"Clusters: {len(clusters_formed)}   |   "
        f"Wave: {station.waves_launched}   |   "
        f"Station reports: {reports}"
    )

    return ax,

# RUN ANIMATION
print("Starting 2D coverage visualization...")
print("- Network links colored by capacity (violet=high, plum=low)")
print("- Same detection / cluster / reporting logic as 3D version")
print("- Monitoring Station tracks all successful reports")
ani = FuncAnimation(fig, animate, frames=range(0, int(SIM_TIME / DT) + 1),
                    interval=60, blit=False)

plt.tight_layout(rect=[0, 0.04, 1, 0.96])
plt.show()

# FINAL STATISTICS
print("\n" + "="*70)
print("SIMULATION COMPLETE – 2D COVERAGE MAP")
print("="*70)

alive_final = sum(1 for d in drones if d.alive)
det_final = sum(u.group_size for u in users if u.detected)
srv_final = sum(u.group_size for u in users if u.served)
tot_final = sum(u.group_size for u in users)

print(f"Duration:                {SIM_TIME} s")
print(f"Drones survived:         {alive_final} / {NUM_DRONES}")
print(f"Avg battery remaining:   {np.mean([d.battery for d in drones if d.alive]) if any(d.alive for d in drones) else 0:.0f} J")
print(f"People detected:         {det_final} / {tot_final}  ({det_final/tot_final*100:.1f}%)")
print(f"People served:           {srv_final} / {tot_final}  ({srv_final/tot_final*100:.1f}%)")
print(f"Clusters formed:         {len(clusters_formed)}")
print(f"Total alerts sent:       {len(operator.notifications)}")
print(f"Reports received at station: {len(station.received_reports)}")

print("\nFirst 10 station reports:")
for i, r in enumerate(station.received_reports[:10], 1):
    print(f" {i}. t={r['time']:3.0f}s  Drone {r['drone_id']}  →  {r['group_size']} pers   "
          f"{r['hops']} hops   {r['capacity']:.1f} Mbps")

print("\n" + "="*70)


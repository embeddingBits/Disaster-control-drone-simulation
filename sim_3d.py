import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D

from config_params import *

# Init
print("3D DISASTER RELIEF DRONE NETWORK SIMULATION")
print(f"Simulation Duration: {SIM_TIME} seconds (extended)")
print(f"Number of Drones: {NUM_DRONES}")
print(f"Area Size: {AREA_SIZE}m x {AREA_SIZE}m")

current_time = 0
operator = OperatorNotification()
tower = Tower(TOWER_POSITION)
station = MonitoringStation(STATION_POSITION)
drones = initialize_drones()
users = initialize_users()
clusters_formed = {}
next_cluster_id = 0

# VISUALIZATION SETUP
fig = plt.figure(figsize=(14, 10))
ax_3d = fig.add_subplot(111, projection='3d')

ax_3d.set_xlim(0, AREA_SIZE)
ax_3d.set_ylim(0, AREA_SIZE)
ax_3d.set_zlim(0, 150)
ax_3d.set_xlabel("X (m)", fontsize=12)
ax_3d.set_ylabel("Y (m)", fontsize=12)
ax_3d.set_zlabel("Altitude (m)", fontsize=12)
ax_3d.set_title("3D UAV Disaster Relief Network with Monitoring Station", fontsize=16, fontweight='bold')

# Initialize 3D plot elements
drone_scatter_3d = ax_3d.scatter([], [], [], c='red', s=150, marker='^', 
                                 edgecolors='black', linewidths=2, label="Drones")
user_scatter_3d = ax_3d.scatter([], [], [], c='gray', s=50, alpha=0.6, label="Undetected")
detected_scatter_3d = ax_3d.scatter([], [], [], c='orange', s=80, marker='*', 
                                    edgecolors='black', linewidths=1, label="Detected")
served_scatter_3d = ax_3d.scatter([], [], [], c='green', s=90, marker='s', 
                                  edgecolors='black', linewidths=1, label="Served")
tower_3d = ax_3d.scatter([TOWER_POSITION[0]], [TOWER_POSITION[1]], [TOWER_POSITION[2]], 
                         c='purple', s=400, marker='s', edgecolors='black', 
                         linewidths=3, label="5G Tower")
station_3d = ax_3d.scatter([STATION_POSITION[0]], [STATION_POSITION[1]], [STATION_POSITION[2]], 
                          c='darkgreen', s=500, marker='D', edgecolors='black', 
                          linewidths=3, label="Monitoring Station")

# Add ground plane grid for reference
xx, yy = np.meshgrid(np.linspace(0, AREA_SIZE, 10), np.linspace(0, AREA_SIZE, 10))
zz = np.zeros_like(xx)
ax_3d.plot_surface(xx, yy, zz, alpha=0.05, color='gray')

# Add tower-to-station wired link (permanent)
tower_station_line = ax_3d.plot([TOWER_POSITION[0], STATION_POSITION[0]], 
                                 [TOWER_POSITION[1], STATION_POSITION[1]],
                                 [TOWER_POSITION[2], STATION_POSITION[2]], 
                                 color='black', alpha=0.9, linewidth=4, 
                                 linestyle='--', label="Wired Link")[0]

ax_3d.legend(loc='upper left', fontsize=9)

# Status text
status_text = fig.text(0.5, 0.02, "", ha='center', fontsize=11,
                      bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))

# Store line objects for 3D links
link_lines_3d = []

# ANIMATION UPDATE FUNCTION
def animate(frame):
    global current_time, next_cluster_id, link_lines_3d
    current_time = frame
    
    # Run simulation step
    G, next_cluster_id = update_simulation(drones, users, tower, station, current_time, 
                                           clusters_formed, next_cluster_id, operator)
    
    alive_drones = [d for d in drones if d.alive]
    
    # Remove old link lines
    for line in link_lines_3d:
        line.remove()
    link_lines_3d = []
    
    # Draw 3D network links
    for d in alive_drones:
        # Tower to drone links
        if f'd{d.id}' in G and G.has_edge(f'd{d.id}', 'tower'):
            edge_data = G[f'd{d.id}']['tower']
            capacity = edge_data['capacity']
            
            if capacity > 70:
                color = 'darkviolet'
                alpha = 0.8
                width = 3
            elif capacity > 40:
                color = 'mediumpurple'
                alpha = 0.7
                width = 2.5
            else:
                color = 'plum'
                alpha = 0.6
                width = 2
            
            line = ax_3d.plot([d.pos[0], TOWER_POSITION[0]], 
                             [d.pos[1], TOWER_POSITION[1]],
                             [d.pos[2], TOWER_POSITION[2]], 
                             color=color, alpha=alpha, linewidth=width)[0]
            link_lines_3d.append(line)
        
        # Drone to drone links
        for d2 in alive_drones:
            if d.id < d2.id and f'd{d.id}' in G and G.has_edge(f'd{d.id}', f'd{d2.id}'):
                edge_data = G[f'd{d.id}'][f'd{d2.id}']
                capacity = edge_data['capacity']
                
                if capacity > 70:
                    color = 'green'
                    alpha = 0.7
                    width = 2
                elif capacity > 40:
                    color = 'orange'
                    alpha = 0.6
                    width = 1.8
                else:
                    color = 'red'
                    alpha = 0.5
                    width = 1.5
                
                line = ax_3d.plot([d.pos[0], d2.pos[0]], 
                                 [d.pos[1], d2.pos[1]],
                                 [d.pos[2], d2.pos[2]], 
                                 color=color, alpha=alpha, linewidth=width)[0]
                link_lines_3d.append(line)
    
    # Update drone positions with colors by mode
    if alive_drones:
        dx, dy, dz = zip(*[d.pos for d in alive_drones])
        colors = []
        for d in alive_drones:
            if d.mode == "CLUSTER":
                colors.append('blue')
            elif d.mode == "RELAY":
                colors.append('cyan')
            else:
                colors.append('red')
        drone_scatter_3d._offsets3d = (dx, dy, dz)
        drone_scatter_3d.set_color(colors)
    else:
        drone_scatter_3d._offsets3d = ([], [], [])
    
    # Update user positions by status
    undetected = [u for u in users if not u.detected]
    detected = [u for u in users if u.detected and not u.served]
    served = [u for u in users if u.served]
    
    if undetected:
        ux, uy, uz = zip(*[u.pos for u in undetected])
        user_scatter_3d._offsets3d = (ux, uy, uz)
    else:
        user_scatter_3d._offsets3d = ([], [], [])
    
    if detected:
        dx, dy, dz = zip(*[u.pos for u in detected])
        detected_scatter_3d._offsets3d = (dx, dy, dz)
    else:
        detected_scatter_3d._offsets3d = ([], [], [])
    
    if served:
        sx, sy, sz = zip(*[u.pos for u in served])
        served_scatter_3d._offsets3d = (sx, sy, sz)
    else:
        served_scatter_3d._offsets3d = ([], [], [])
    
    # Update status bar
    alive_count = len(alive_drones)
    detected_people = sum(u.group_size for u in users if u.detected)
    served_people = sum(u.group_size for u in users if u.served)
    total_people = sum(u.group_size for u in users)
    total_throughput = sum(u.throughput for u in users)
    avg_battery = np.mean([d.battery for d in alive_drones]) if alive_drones else 0
    reports_received = len(station.received_reports)
    
    status_text.set_text(
        f"Time: {frame}s / {SIM_TIME}s  |  "
        f"Drones: {alive_count}/{NUM_DRONES}  |  "
        f"Avg Battery: {avg_battery:.0f}J ({100*avg_battery/BATTERY_INIT:.1f}%)  |  "
        f"Detected: {detected_people}/{total_people}  |  "
        f"Served: {served_people}/{total_people} ({100*served_people/max(1,total_people):.1f}%)  |  "
        f"Throughput: {total_throughput:.1f} Mbps  |  "
        f"Clusters: {len(clusters_formed)}  |  "
        f"Station Reports: {reports_received}"
    )
    
    return (drone_scatter_3d, user_scatter_3d, detected_scatter_3d, 
            served_scatter_3d, tower_3d, station_3d, status_text)

# RUN ANIMATION
print("Starting 3D visualization...")
print("- Shows network topology in 3D space")
print("- Link colors indicate capacity (violet=high, plum=low)")
print("- Drone colors: Red=SEARCH, Blue=CLUSTER, Cyan=RELAY")
print("- Monitoring Station receives all detection reports via 5G Tower")

ani = FuncAnimation(fig, animate, frames=range(0, SIM_TIME, DT),
                    interval=50, blit=False)

plt.tight_layout()
plt.show()

# FINAL STATISTICS
print("\n" + "="*70)
print("SIMULATION COMPLETE - 3D VIEW WITH MONITORING STATION")
print("="*70)

final_detected = sum(u.group_size for u in users if u.detected)
final_served = sum(u.group_size for u in users if u.served)
total_people = sum(u.group_size for u in users)

print(f"\nFinal Statistics:")
print(f"  • Duration: {SIM_TIME}s")
print(f"  • Drones Survived: {sum(d.alive for d in drones)}/{NUM_DRONES}")
print(f"  • Average Battery: {np.mean([d.battery for d in drones if d.alive]):.0f}J")
print(f"  • People Detected: {final_detected}/{total_people} ({100*final_detected/total_people:.1f}%)")
print(f"  • People Served: {final_served}/{total_people} ({100*final_served/total_people:.1f}%)")
print(f"  • Coverage Rate: {100*final_served/total_people:.1f}%")
print(f"  • Clusters Formed: {len(clusters_formed)}")
print(f"  • Total Alerts: {len(operator.notifications)}")
print(f"  • Reports Received at Station: {len(station.received_reports)}")

print("\nMonitoring Station Report Summary:")
for i, report in enumerate(station.received_reports[:15]):
    print(f"  {i+1}. t={report['time']}s - Drone {report['drone_id']} detected "
          f"{report['group_size']} person(s) via {report['hops']}-hop path "
          f"(capacity: {report['capacity']:.1f} Mbps)")
    
if len(station.received_reports) > 15:
    print(f"  ... and {len(station.received_reports) - 15} more reports")

print("\nCommunication Flow:")
print("  Drone → [Relay Drones] → 5G Tower → Monitoring Station")
print("  Small groups (1-3 people): Detected and reported to station")
print("  Large groups (10+ people): Cluster formation + continuous 5G service")


import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import networkx as nx
import random

# ==========================================
# 1. SIMULATION CONSTANTS (The "Engine" Settings)
# ==========================================
AREA_SIZE = 600
SIM_TIME = 800
DT = 1.0  # Time step

# Drone Specs
NUM_DRONES = 12
DRONE_SPEED = 8.0
DRONE_ALTITUDE = 90
RELAY_ALTITUDE = 120  # Relays fly higher
COMM_RANGE = 250     # 5G Range
SENSING_RANGE = 120   # Camera Range
BATTERY_MAX = 5000

# Base Station
TOWER_POS = np.array([50, 50, 0])
TOWER_HEIGHT = 100

# Physics
BUILDING_COUNT = 8
BUILDING_SIZE_RANGE = (60, 100)

# Colors (Hex for Sci-Fi HUD look)
COLOR_BG = '#0d0d0d'      # Dark background
COLOR_GRID = '#1f4045'    # Cyan-ish grid
COLOR_DRONE_SEARCH = '#00ccff' # Cyan
COLOR_DRONE_RELAY = '#ff00ff'  # Magenta
COLOR_USER_CRITICAL = '#ff3333' # Red
COLOR_USER_STABLE = '#00ff66'   # Green
COLOR_BUILDING = '#262626'      # Dark Grey

# ==========================================
# 2. ENTITY CLASSES
# ==========================================

class Building:
    def __init__(self, x, y, width, depth, height):
        self.x, self.y = x, y
        self.w, self.d, self.h = width, depth, height
        self.center = np.array([x + width/2, y + depth/2, height/2])

    def contains_point(self, pos):
        """Check if a point is inside the building"""
        return (self.x <= pos[0] <= self.x + self.w and
                self.y <= pos[1] <= self.y + self.d and
                0 <= pos[2] <= self.h)
    
    def overlaps(self, other, buffer=10):
        """Check if this building overlaps with another"""
        return (self.x < other.x + other.w + buffer and 
                self.x + self.w + buffer > other.x and
                self.y < other.y + other.d + buffer and 
                self.y + self.d + buffer > other.y)

class User:
    def __init__(self, uid, pos, priority="STABLE"):
        self.id = uid
        self.pos = np.array(pos, dtype=float)
        self.priority = priority # CRITICAL or STABLE
        self.detected = False
        self.served = False
        self.data_stream_active = False

class Drone:
    def __init__(self, uid, pos):
        self.id = uid
        self.pos = np.array(pos, dtype=float)
        self.target = None
        self.mode = "SEARCH" # SEARCH, RELAY, RETURN
        self.battery = BATTERY_MAX
        self.connected_users = []
        self.path_to_tower = []
    
    def move(self, obstacles):
        if self.target is None: return

        # Vector to target
        direction = self.target - self.pos
        dist = np.linalg.norm(direction)
        
        if dist < 1.0: return # Arrived

        # Normalize and move
        step = (direction / dist) * min(DRONE_SPEED, dist)
        
        # Simple Collision Avoidance (Jump over buildings)
        next_pos = self.pos + step
        for b in obstacles:
            if b.contains_point(next_pos):
                next_pos[2] = b.h + 10 # Fly up instantly to avoid crash (simulation abstraction)
        
        self.pos = next_pos
        self.battery -= 1 if self.mode == "SEARCH" else 0.5

# ==========================================
# 3. CORE LOGIC
# ==========================================

def generate_city():
    """Generates random buildings and users without overlap"""
    buildings = []
    attempts = 0
    max_attempts = 100
    
    while len(buildings) < BUILDING_COUNT and attempts < max_attempts:
        x = random.randint(100, AREA_SIZE-100)
        y = random.randint(100, AREA_SIZE-100)
        w = random.randint(*BUILDING_SIZE_RANGE)
        d = random.randint(*BUILDING_SIZE_RANGE)
        h = random.randint(40, 150)
        
        new_b = Building(x, y, w, d, h)
        
        # Check collision with tower area
        dist_to_tower_sq = (x - TOWER_POS[0])**2 + (y - TOWER_POS[1])**2
        if dist_to_tower_sq < 100**2: # Keep 100m away from tower
            attempts += 1
            continue
            
        # Check collision with existing buildings
        collision = False
        for b in buildings:
            if new_b.overlaps(b):
                collision = True
                break
        
        if not collision:
            buildings.append(new_b)
        
        attempts += 1
    
    users = []
    # Cluster users near buildings (disaster scenario)
    for i, b in enumerate(buildings):
        # 1-3 victims per building area
        for _ in range(random.randint(1, 3)):
            # Add noise to position
            ux = b.x + b.w/2 + random.randint(-40, 40)
            uy = b.y + b.d/2 + random.randint(-40, 40)
            # Ensure users stay within bounds
            ux = np.clip(ux, 0, AREA_SIZE)
            uy = np.clip(uy, 0, AREA_SIZE)
            
            priority = "CRITICAL" if random.random() < 0.4 else "STABLE"
            users.append(User(len(users), [ux, uy, 0], priority))
            
    return buildings, users

def get_signal_strength(p1, p2, obstacles):
    """Calculates signal based on distance and Line of Sight"""
    dist = np.linalg.norm(p1 - p2)
    if dist > COMM_RANGE:
        return 0
    
    # Check Line of Sight (simplified ray trace)
    midpoint = (p1 + p2) / 2
    for b in obstacles:
        # If midpoint intersects a building, heavy penalty
        if b.contains_point(midpoint):
            return 0 # Signal blocked by concrete
            
    return 1 - (dist / COMM_RANGE)**2 # Normalized 0.0 to 1.0

def update_network(drones, tower_pos, buildings):
    G = nx.Graph()
    G.add_node("TOWER", pos=np.array([tower_pos[0], tower_pos[1], TOWER_HEIGHT]))

    # Add Drones
    for d in drones:
        G.add_node(d.id, pos=d.pos)

    # 1. Link Drones to Tower
    for d in drones:
        sig = get_signal_strength(d.pos, G.nodes["TOWER"]['pos'], buildings)
        if sig > 0:
            G.add_edge(d.id, "TOWER", weight=1/sig, signal=sig)

    # 2. Link Drones to Drones (Mesh)
    for i in range(len(drones)):
        for j in range(i+1, len(drones)):
            d1, d2 = drones[i], drones[j]
            sig = get_signal_strength(d1.pos, d2.pos, buildings)
            if sig > 0.1: # Threshold to filter weak links
                G.add_edge(d1.id, d2.id, weight=1/sig, signal=sig)
    
    return G

# ==========================================
# 4. SWARM INTELLIGENCE ("The Winning Feature")
# ==========================================
def run_swarm_logic(drones, users, G, current_time):
    
    active_searchers = [d for d in drones if d.mode == "SEARCH"]
    
    # 1. Update Detection
    for d in drones:
        d.connected_users = []
        for u in users:
            if not u.detected:
                dist = np.linalg.norm(d.pos - u.pos)
                if dist < SENSING_RANGE:
                    u.detected = True # Found them!
                    
            if u.detected and not u.served:
                dist = np.linalg.norm(d.pos - u.pos)
                if dist < SENSING_RANGE:
                    d.connected_users.append(u)

    # 2. The "Self-Healing" Relay Logic
    # If a searcher finds a victim but has NO connection to Tower,
    # Dispatch an idle drone to act as a bridge.
    
    for d in active_searchers:
        has_path = False
        try:
            if nx.has_path(G, d.id, "TOWER"):
                has_path = True
        except:
            pass
            
        if not has_path and d.connected_users:
            # SEARCHER IS DISCONNECTED BUT HAS VICTIMS! SCREAM FOR HELP.
            # Find nearest other drone
            helpers = sorted(drones, key=lambda x: np.linalg.norm(x.pos - d.pos))
            
            for h in helpers:
                if h.id != d.id and h.mode != "RELAY":
                    # Deploy logic: Move helper to midpoint
                    midpoint = (d.pos + np.array([TOWER_POS[0], TOWER_POS[1], TOWER_HEIGHT])) / 2
                    midpoint[2] = RELAY_ALTITUDE
                    
                    h.mode = "RELAY"
                    h.target = midpoint
                    # Hack: Stop loop so we don't convert everyone
                    break

# ==========================================
# 5. INITIALIZATION
# ==========================================
buildings, users = generate_city()
drones = []
# Initialize drones in a circle around base
for i in range(NUM_DRONES):
    angle = (2 * np.pi * i) / NUM_DRONES
    dx = TOWER_POS[0] + 20 * np.cos(angle)
    dy = TOWER_POS[1] + 20 * np.sin(angle)
    d = Drone(i, [dx, dy, DRONE_ALTITUDE])
    
    # Send scouts out to random corners of map
    tx = random.uniform(100, AREA_SIZE-100)
    ty = random.uniform(100, AREA_SIZE-100)
    d.target = np.array([tx, ty, DRONE_ALTITUDE])
    drones.append(d)

# ==========================================
# 6. VISUALIZATION (Sci-Fi Theme)
# ==========================================
fig = plt.figure(figsize=(16, 9), facecolor=COLOR_BG)
ax = fig.add_subplot(111, projection='3d')
ax.set_facecolor(COLOR_BG)

# Style axes to look like a Hologram
for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
    axis.set_pane_color((0, 0, 0, 0)) # Transparent
    axis._axinfo["grid"]['color'] = COLOR_GRID
    axis._axinfo["grid"]['alpha'] = 0.5

ax.set_xlim(0, AREA_SIZE)
ax.set_ylim(0, AREA_SIZE)
ax.set_zlim(0, 200)
ax.set_title("AERO-NET: AUTONOMOUS DISASTER RESPONSE SWARM", color='white', fontname='monospace', fontweight='bold')
ax.set_xlabel("Sector X (m)", color='gray')
ax.set_ylabel("Sector Y (m)", color='gray')
ax.set_zlabel("Alt (m)", color='gray')

# Legend Elements (Empty placeholders to update)
scatter_drones = ax.scatter([], [], [], s=100, c=COLOR_DRONE_SEARCH, marker='^', edgecolors='white', alpha=1.0)
scatter_users_undel = ax.scatter([], [], [], s=30, c='gray', marker='x', alpha=0.3)
scatter_users_crit = ax.scatter([], [], [], s=80, c=COLOR_USER_CRITICAL, marker='o', edgecolors='white', alpha=0.0)
scatter_users_stab = ax.scatter([], [], [], s=50, c=COLOR_USER_STABLE, marker='o', edgecolors='black', alpha=0.0)
line_collection = []

# Status HUD
text_stats = fig.text(0.02, 0.05, "SYSTEM INITIALIZING...", 
                      color=COLOR_DRONE_SEARCH, fontname='monospace', fontsize=12,
                      bbox={'facecolor': 'black', 'alpha': 0.8, 'pad': 10, 'edgecolor': COLOR_GRID})

# Render Buildings (Static)
def plot_cube(pos, size, color=COLOR_BUILDING, alpha=0.3):
    x, y, z = pos
    w, d, h = size
    # Define vertices for a cube
    xx = [x, x+w, x+w, x, x, x+w, x+w, x]
    yy = [y, y, y+d, y+d, y, y, y+d, y+d]
    zz = [0, 0, 0, 0, h, h, h, h]
    
    points = np.array([[x, y, 0], [x+w, y, 0], [x+w, y+d, 0], [x, y+d, 0],
                       [x, y, h], [x+w, y, h], [x+w, y+d, h], [x, y+d, h]])
    
    faces = [[points[0], points[1], points[5], points[4]],
             [points[7], points[6], points[2], points[3]],
             [points[0], points[4], points[7], points[3]],
             [points[1], points[2], points[6], points[5]],
             [points[0], points[1], points[2], points[3]],
             [points[4], points[5], points[6], points[7]]]
    
    collection = Poly3DCollection(faces, linewidths=1, edgecolors=COLOR_GRID, alpha=alpha)
    collection.set_facecolor(color)
    ax.add_collection3d(collection)

# Draw Tower
ax.plot([TOWER_POS[0], TOWER_POS[0]], [TOWER_POS[1], TOWER_POS[1]], [0, TOWER_HEIGHT], c='white', linewidth=4)
ax.text(TOWER_POS[0], TOWER_POS[1], TOWER_HEIGHT+10, "HQ", color="white")

# Draw City
print("Rendering Environment...")
for b in buildings:
    plot_cube([b.x, b.y, 0], [b.w, b.d, b.h])

# ==========================================
# 7. ANIMATION LOOP
# ==========================================

lines = [] # store line objects to remove them later

def animate(i):
    global lines
    current_time = i * DT
    
    # Clean previous lines
    for line in lines:
        line.remove()
    lines = []
    
    # 1. Update Physics
    for d in drones:
        d.move(buildings)
        # Random new target if reached old one (Simulate patrolling)
        if np.linalg.norm(d.pos - d.target) < 2.0 and d.mode == "SEARCH":
            d.target = np.array([random.uniform(50, AREA_SIZE-50), 
                                 random.uniform(50, AREA_SIZE-50), 
                                 DRONE_ALTITUDE])
            
    # 2. Update Logic (Graph & Swarm)
    G = update_network(drones, TOWER_POS, buildings)
    run_swarm_logic(drones, users, G, current_time)
    
    # 3. Update Visuals - Drones
    d_pos = np.array([d.pos for d in drones])
    # Color logic: Relay = Pink, Search = Cyan
    c_list = [COLOR_DRONE_RELAY if d.mode == "RELAY" else COLOR_DRONE_SEARCH for d in drones]
    scatter_drones._offsets3d = (d_pos[:, 0], d_pos[:, 1], d_pos[:, 2])
    scatter_drones.set_color(c_list)
    
    # 4. Update Visuals - Users
    # Split into Critical vs Stable vs Undetected
    undetected = [u.pos for u in users if not u.detected]
    detected_crit = [u.pos for u in users if u.detected and u.priority == "CRITICAL"]
    detected_stab = [u.pos for u in users if u.detected and u.priority == "STABLE"]
    
    if undetected: 
        uds = np.array(undetected)
        scatter_users_undel._offsets3d = (uds[:, 0], uds[:, 1], uds[:, 2])
    else: scatter_users_undel._offsets3d = ([],[],[])
        
    if detected_crit: 
        dcs = np.array(detected_crit)
        scatter_users_crit._offsets3d = (dcs[:, 0], dcs[:, 1], dcs[:, 2])
        # Force alpha to 1.0 using set_facecolor/set_edgecolor if needed, but scatter set_alpha works too
        # scatter_users_crit.set_alpha(1.0) 
        # Note: scatter set_alpha sets alpha for ALL points. 
        # But we manipulate offsets, so it's safer to control alpha via c= argument or set_alpha globally for the collection
        scatter_users_crit.set_alpha(1.0)
    else: scatter_users_crit._offsets3d = ([],[],[])

    if detected_stab:
        dss = np.array(detected_stab)
        scatter_users_stab._offsets3d = (dss[:, 0], dss[:, 1], dss[:, 2])
        scatter_users_stab.set_alpha(0.8)
    else: scatter_users_stab._offsets3d = ([],[],[])

    # 5. Draw Network Links (Sci-Fi Lasers)
    for u, v in G.edges():
        pos_u = G.nodes[u]['pos']
        pos_v = G.nodes[v]['pos']
        signal = G.edges[u, v]['signal']
        
        # Color gradient based on signal quality
        # White/Green = Strong, Yellow/Red = Weak
        if signal > 0.8: link_color = 'white'
        elif signal > 0.5: link_color = COLOR_DRONE_SEARCH
        else: link_color = 'red'
        
        l, = ax.plot([pos_u[0], pos_v[0]], [pos_u[1], pos_v[1]], [pos_u[2], pos_v[2]], 
                     c=link_color, alpha=0.5, linewidth=1.5)
        lines.append(l)

    # 6. Check for Valid Paths from Victims to Tower
    served_count = 0
    crit_count = 0
    
    for u in users:
        if not u.detected: continue
        
        # Find closest drone
        dists = [(d, np.linalg.norm(d.pos - u.pos)) for d in drones]
        closest_drone, dist = min(dists, key=lambda x: x[1])
        
        if dist < SENSING_RANGE:
            # Check graph for path to tower
            try:
                if nx.has_path(G, closest_drone.id, "TOWER"):
                    served_count += 1
                    u.served = True
                    # Draw visual link user -> drone
                    line_col = COLOR_USER_CRITICAL if u.priority == "CRITICAL" else COLOR_USER_STABLE
                    if u.priority == "CRITICAL": crit_count += 1
                    
                    l, = ax.plot([u.pos[0], closest_drone.pos[0]], 
                                 [u.pos[1], closest_drone.pos[1]], 
                                 [u.pos[2], closest_drone.pos[2]], 
                                 c=line_col, linestyle='--', alpha=0.8, linewidth=1)
                    lines.append(l)
            except:
                pass

    # 7. Update HUD Stats
    hud = (
        f"AERO-NET // SYSTEM STATUS: ONLINE\n"
        f"TIME: {current_time:.1f}s\n"
        f"-----------------------------\n"
        f"ACTIVE DRONES : {NUM_DRONES}\n"
        f"RELAY MODES   : {[d.mode for d in drones].count('RELAY')}\n"
        f"BATTERY AVG   : {int(np.mean([d.battery for d in drones]))} mAh\n"
        f"-----------------------------\n"
        f"CIVILIANS LOCATED : {sum(u.detected for u in users)} / {len(users)}\n"
        f"CRITICAL LINKS    : {crit_count} (ACTIVE STREAM)\n"
        f"TOTAL UPLINKS     : {served_count}\n"
    )
    text_stats.set_text(hud)

# Start Animation
ani = FuncAnimation(fig, animate, frames=range(0, SIM_TIME), interval=40, blit=False)

print("------------------------------------------")
print("  LAUNCHING AERO-NET SIMULATION V.2.0")
print("  Feature: Autonomous Swarm Relay System")
print("------------------------------------------")
plt.show()

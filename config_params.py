import numpy as np
import networkx as nx

# Speed is in m/s and distance in meters
# Bandwidth in Mbps
# Simulation parameters
AREA_SIZE = 500  
SIM_TIME = 600  # seconds 
DT = 1  # time step

# DRONE SPECIFICATIONS
NUM_DRONES = 8
DRONE_SPEED = 5.0  
DRONE_ALTITUDE = 80 
COVERAGE_RADIUS = 120 
SEARCH_RADIUS = 150  # For victim detection
BATTERY_INIT = 15000
BATTERY_DRAIN_IDLE = 15  
BATTERY_DRAIN_MOVING = 25
BATTERY_DRAIN_RELAY = 30 

# 5G NETWORK PARAMETERS
TOWER_POSITION = np.array([250, 250, 100])
STATION_POSITION = np.array([250, 250, 0])
MAX_5G_RANGE = 300
LINK_CAPACITY_MAX = 100
TOWER_TO_STATION_CAPACITY = 1000  
RELAY_HOP_PENALTY = 0.7  # capacity reduction per hop
MIN_CLUSTER_SIZE = 3  # drones needed for cluster
CLUSTER_FORMATION_THRESHOLD = 10  # users to trigger cluster

# USER/VICTIM PARAMETERS
NUM_ISOLATED_VICTIMS = 5  # 1-3 people scattered
NUM_CLUSTER_ZONES = 2  # zones with 10+ people
USERS_PER_CLUSTER = 15

# ENTITY CLASSES

class Drone:
    """Drone agent with battery, positioning, and mode control"""
    
    def __init__(self, drone_id, pos):
        self.id = drone_id
        self.pos = np.array(pos, dtype=float)
        self.battery = BATTERY_INIT
        self.alive = True
        self.target = None
        self.mode = "SEARCH"  # SEARCH, RESCUE, RELAY, CLUSTER
        self.cluster_id = None
        self.detected_victims = []
        
    def move(self):
        """Move drone towards target position"""
        if not self.alive or self.target is None:
            return
        direction = self.target - self.pos
        dist = np.linalg.norm(direction[:2])  # 2D distance
        if dist < 1e-2:
            return
        step = min(DRONE_SPEED * DT, dist)
        self.pos[:2] += direction[:2] / dist * step
        
    def drain(self):
        """Drain battery based on current mode"""
        if self.mode == "RELAY" or self.mode == "CLUSTER":
            drain = BATTERY_DRAIN_RELAY * DT
        elif self.target is not None and np.linalg.norm(self.target - self.pos) > 1:
            drain = BATTERY_DRAIN_MOVING * DT
        else:
            drain = BATTERY_DRAIN_IDLE * DT
            
        self.battery -= drain
        if self.battery <= 0:
            self.battery = 0
            self.alive = False
            
    def scan_for_victims(self, users):
        """Detect victims within search radius"""
        new_detections = []
        for u in users:
            if u.detected:
                continue
            dist = np.linalg.norm(self.pos[:2] - u.pos[:2])
            if dist <= SEARCH_RADIUS:
                u.detected = True
                u.detected_by = self.id
                new_detections.append(u)
                self.detected_victims.append(u.id)
        return new_detections


class User:
    """User/victim entity with connectivity status"""
    
    def __init__(self, uid, pos, group_size=1):
        self.id = uid
        self.pos = np.array(pos, dtype=float)
        self.group_size = group_size  # 1-3 for isolated, 10+ for clusters
        self.served = False
        self.detected = False
        self.detected_by = None
        self.throughput = 0  # Mbps
        self.connected_drone = None
        self.hops_to_tower = None


class Tower:
    """5G Tower base station"""
    
    def __init__(self, pos):
        self.pos = np.array(pos, dtype=float)
        self.connected_drones = []


class MonitoringStation:
    """Drone monitoring base station - receives reports from field via tower"""
    
    def __init__(self, pos):
        self.pos = np.array(pos, dtype=float)
        self.received_reports = []
        self.active_drones = []
        
    def receive_report(self, report):
        """Receive detection report from tower"""
        self.received_reports.append(report)


class OperatorNotification:
    """System to notify operator of detections"""
    
    def __init__(self):
        self.notifications = []
        
    def alert_victim_detected(self, drone_id, user, time, path_info=None):
        msg = {
            'time': time,
            'drone_id': drone_id,
            'user_id': user.id,
            'group_size': user.group_size,
            'path_info': path_info
        }
        self.notifications.append(msg)
        
        if path_info:
            print(f"[ALERT t={time}s] Drone {drone_id} detected {user.group_size} "
                  f"person(s) at ({user.pos[0]:.1f}, {user.pos[1]:.1f})")
            print(f"  → Report path to STATION: {' → '.join(path_info['path'])} "
                  f"({path_info['hops']} hops, {path_info['capacity']:.1f} Mbps)")
        else:
            print(f"[ALERT t={time}s] Drone {drone_id} detected {user.group_size} "
                  f"person(s) at ({user.pos[0]:.1f}, {user.pos[1]:.1f})")
        
    def alert_cluster_formed(self, cluster_id, drones, users, time):
        total_people = sum(u.group_size for u in users)
        self.notifications.append({
            'time': time,
            'cluster_id': cluster_id,
            'total_people': total_people,
        })
        print(f"[CLUSTER t={time}s] Cluster {cluster_id} formed with "
              f"{len(drones)} drones serving {total_people} people")


# NETWORK TOPOLOGY & LINK MODELING

def calculate_link_capacity(dist, los=True):
    """Calculate link capacity based on distance and line-of-sight"""
    if dist > MAX_5G_RANGE:
        return 0
    
    # Path loss model (simplified)
    base_capacity = LINK_CAPACITY_MAX
    attenuation = (dist / MAX_5G_RANGE) ** 2
    los_factor = 1.0 if los else 0.6
    
    capacity = base_capacity * (1 - attenuation) * los_factor
    return max(0, capacity)


def build_network_graph(drones, tower, station):
    """Build network topology graph including monitoring station"""
    G = nx.DiGraph()
    
    # Add monitoring station node
    G.add_node('station', pos=station.pos, type='station')
    
    # Add tower node
    G.add_node('tower', pos=tower.pos, type='tower')
    
    # Add wired link: Tower <--> Station (bidirectional, high capacity)
    G.add_edge('tower', 'station', 
               capacity=TOWER_TO_STATION_CAPACITY, 
               distance=0, 
               link_type='wired')
    G.add_edge('station', 'tower', 
               capacity=TOWER_TO_STATION_CAPACITY, 
               distance=0, 
               link_type='wired')
    
    # Add drone nodes
    for d in drones:
        if d.alive:
            G.add_node(f'd{d.id}', pos=d.pos, type='drone', drone=d)
    
    # Add edges (links)
    for d in drones:
        if not d.alive:
            continue
            
        # Drone to tower link
        dist = np.linalg.norm(d.pos - tower.pos)
        capacity = calculate_link_capacity(dist)
        if capacity > 0:
            G.add_edge(f'd{d.id}', 'tower', 
                      capacity=capacity, distance=dist, hops=1)
        
        # Drone to drone links
        for d2 in drones:
            if d2.alive and d.id != d2.id:
                dist = np.linalg.norm(d.pos - d2.pos)
                capacity = calculate_link_capacity(dist)
                if capacity > 0:
                    G.add_edge(f'd{d.id}', f'd{d2.id}',
                              capacity=capacity, distance=dist)
    
    return G


def find_best_path_to_tower(G, drone_id):
    """Find best path from drone to tower using capacity-weighted shortest path"""
    try:
        path = nx.shortest_path(G, f'd{drone_id}', 'tower', 
                               weight=lambda u, v, d: 1/max(d['capacity'], 1))
        
        # Calculate effective capacity (reduced by hops)
        min_capacity = float('inf')
        for i in range(len(path)-1):
            edge_cap = G[path[i]][path[i+1]]['capacity']
            min_capacity = min(min_capacity, edge_cap)
        
        effective_capacity = min_capacity * (RELAY_HOP_PENALTY ** (len(path)-2))
        return path, len(path)-1, effective_capacity
    except nx.NetworkXNoPath:
        return None, None, 0


def find_path_to_station(G, drone_id):
    """Find path from drone to monitoring station via tower"""
    try:
        # Path: Drone → [relay drones] → Tower → Station
        path = nx.shortest_path(G, f'd{drone_id}', 'station', 
                               weight=lambda u, v, d: 1/max(d['capacity'], 1))
        
        # Calculate effective capacity
        min_capacity = float('inf')
        for i in range(len(path)-1):
            edge_cap = G[path[i]][path[i+1]]['capacity']
            min_capacity = min(min_capacity, edge_cap)
        
        # Count wireless hops (exclude tower-station wired link)
        wireless_hops = len([p for p in path if p.startswith('d')]) - 1
        effective_capacity = min_capacity * (RELAY_HOP_PENALTY ** max(0, wireless_hops))
        
        return path, len(path)-1, effective_capacity
    except nx.NetworkXNoPath:
        return None, None, 0


# CLUSTERING & COORDINATION

def detect_user_clusters(users):
    """Detect groups of users for cluster formation"""
    clusters = []
    visited = set()
    
    for u in users:
        if u.id in visited or u.group_size < CLUSTER_FORMATION_THRESHOLD:
            continue
            
        # Find nearby users forming a cluster
        cluster = [u]
        visited.add(u.id)
        
        for u2 in users:
            if u2.id in visited:
                continue
            dist = np.linalg.norm(u.pos[:2] - u2.pos[:2])
            if dist < 100:  # cluster proximity threshold
                cluster.append(u2)
                visited.add(u2.id)
        
        if sum(usr.group_size for usr in cluster) >= CLUSTER_FORMATION_THRESHOLD:
            clusters.append(cluster)
    
    return clusters


def form_drone_cluster(drones, cluster_center, cluster_id):
    """Assign drones to form a cluster formation"""
    available = [d for d in drones if d.alive and d.mode == "SEARCH"]
    
    if len(available) < MIN_CLUSTER_SIZE:
        return []
    
    # Select closest drones
    distances = [(d, np.linalg.norm(d.pos[:2] - cluster_center[:2])) 
                 for d in available]
    distances.sort(key=lambda x: x[1])
    
    selected = distances[:MIN_CLUSTER_SIZE]
    
    # Arrange in triangular formation
    for i, (d, _) in enumerate(selected):
        angle = i * (2 * np.pi / MIN_CLUSTER_SIZE)
        offset = COVERAGE_RADIUS * 0.6
        target_pos = cluster_center.copy()
        target_pos[0] += offset * np.cos(angle)
        target_pos[1] += offset * np.sin(angle)
        
        d.target = target_pos
        d.mode = "CLUSTER"
        d.cluster_id = cluster_id
    
    return [d for d, _ in selected]


# SIMULATION UPDATE LOGIC

def update_simulation(drones, users, tower, station, current_time, clusters_formed, 
                      next_cluster_id, operator):
    """Main simulation update step"""
    
    # 1. Build network topology
    G = build_network_graph(drones, tower, station)
    
    # 2. Scan for victims and report to monitoring station
    for d in drones:
        if d.alive and d.mode in ["SEARCH", "RESCUE"]:
            detections = d.scan_for_victims(users)
            
            for u in detections:
                # Check if drone can reach monitoring station
                path, hops, capacity = find_path_to_station(G, d.id)
                
                if path and capacity > 0:
                    # Successfully report to monitoring station
                    path_info = {
                        'path': path,
                        'hops': hops,
                        'capacity': capacity
                    }
                    
                    report = {
                        'time': current_time,
                        'drone_id': d.id,
                        'user_id': u.id,
                        'group_size': u.group_size,
                        'location': u.pos.copy(),
                        'path': path,
                        'hops': hops,
                        'capacity': capacity
                    }
                    station.receive_report(report)
                    operator.alert_victim_detected(d.id, u, current_time, path_info)
                else:
                    # No path to station - report failed
                    print(f"[FAILED t={current_time}s] Drone {d.id} detected "
                          f"{u.group_size} person(s) but NO PATH to monitoring station!")
                    operator.alert_victim_detected(d.id, u, current_time, None)
    
    # 3. Detect and handle clusters
    user_clusters = detect_user_clusters(users)
    for cluster_users in user_clusters:
        cluster_center = np.mean([u.pos for u in cluster_users], axis=0)
        
        # Check if cluster already handled
        cluster_key = tuple(sorted([u.id for u in cluster_users]))
        if cluster_key not in clusters_formed:
            cluster_drones = form_drone_cluster(drones, cluster_center, next_cluster_id)
            if cluster_drones:
                clusters_formed[cluster_key] = next_cluster_id
                operator.alert_cluster_formed(next_cluster_id, cluster_drones, 
                                             cluster_users, current_time)
                next_cluster_id += 1
    
    # 4. Update drone targets for non-clustered drones
    for d in drones:
        if not d.alive:
            continue
            
        if d.mode == "SEARCH":
            # Head towards nearest undetected victim
            undetected = [u for u in users if not u.detected]
            if undetected:
                distances = [(u, np.linalg.norm(d.pos[:2] - u.pos[:2])) 
                            for u in undetected]
                nearest = min(distances, key=lambda x: x[1])[0]
                d.target = nearest.pos.copy()
                d.target[2] = DRONE_ALTITUDE
            else:
                d.target = d.pos.copy()
    
    # 5. Update coverage and throughput
    for u in users:
        u.served = False
        u.throughput = 0
        u.connected_drone = None
        u.hops_to_tower = None
        
        for d in drones:
            if not d.alive:
                continue
            dist_2d = np.linalg.norm(d.pos[:2] - u.pos[:2])
            if dist_2d <= COVERAGE_RADIUS:
                # Find path to tower
                path, hops, capacity = find_best_path_to_tower(G, d.id)
                if path and capacity > 0:
                    u.served = True
                    u.throughput = capacity
                    u.connected_drone = d.id
                    u.hops_to_tower = hops
                    break
    
    # 6. Move drones and drain batteries
    for d in drones:
        if d.alive:
            d.move()
            d.drain()
    
    return G, next_cluster_id


# INITIALIZATION FUNCTIONS

def initialize_drones():
    """Initialize drone fleet"""
    drones = []
    for i in range(NUM_DRONES):
        angle = i * (2 * np.pi / NUM_DRONES)
        radius = AREA_SIZE * 0.4
        x = AREA_SIZE/2 + radius * np.cos(angle)
        y = AREA_SIZE/2 + radius * np.sin(angle)
        drone = Drone(i, [x, y, DRONE_ALTITUDE])
        drones.append(drone)
    return drones


def initialize_users():
    """Initialize users/victims"""
    users = []
    uid = 0

    # Isolated victims (1-3 people)
    for _ in range(NUM_ISOLATED_VICTIMS):
        x = np.random.uniform(50, AREA_SIZE-50)
        y = np.random.uniform(50, AREA_SIZE-50)
        group_size = np.random.randint(1, 4)
        users.append(User(uid, [x, y, 0], group_size))
        uid += 1

    # Cluster zones (10+ people)
    cluster_centers = [
        (350, 150),
        (150, 350),
    ]
    for cx, cy in cluster_centers:
        for i in range(USERS_PER_CLUSTER):
            x = cx + np.random.randn() * 25
            y = cy + np.random.randn() * 25
            group_size = np.random.randint(10, 16) if i == 0 else np.random.randint(1, 3)
            users.append(User(uid, [x, y, 0], group_size))
            uid += 1
    
    return users

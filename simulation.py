import numpy as np
import networkx as nx
from .models import Drone, User

def run_simulation(config, seed=0):
    np.random.seed(seed)

    drones = [Drone(i, config.area_size, config.battery_init)
              for i in range(config.num_drones)]
    users = [User(config.area_size)
             for _ in range(config.num_users)]

    G = nx.Graph()
    throughput_ts = []

    for t in range(config.sim_time):
        G.clear()

        # Move drones
        for d in drones:
            d.move()
            if d.alive:
                G.add_node(d.id)

        # Drone-to-drone links
        for i, d1 in enumerate(drones):
            if not d1.alive:
                continue
            for d2 in drones[i+1:]:
                if not d2.alive:
                    continue
                dist = np.linalg.norm(d1.pos - d2.pos)
                if dist < config.search_radius:
                    capacity = max(1, 100 - dist * 0.5)
                    G.add_edge(d1.id, d2.id, capacity=capacity)

        # User detection & service
        total_thr = 0
        for u in users:
            for d in drones:
                if not d.alive:
                    continue
                if np.linalg.norm(u.pos - d.pos) < config.coverage_radius:
                    u.detected = True
                    u.served = True
                    u.throughput = np.random.uniform(5, 20)
                    total_thr += u.throughput
                    break

        throughput_ts.append(total_thr)

    return {
        "throughput_timeseries": throughput_ts,
        "users": users,
        "drones": drones
    }

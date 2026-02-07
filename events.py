import simpy
from network import build_network
import networkx as nx

def drone_process(env, drone, target, speed):
    while drone.alive:
        from mobility import move_towards
        move_towards(drone, target, speed, dt=1)
        drone.drain(20)
        yield env.timeout(1)


def traffic_process(env, drones, users, base_stations, stats):
    while True:
        G = build_network(drones, users, base_stations)

        served = 0
        for u in users:
            try:
                path = nx.shortest_path(G, f"U{u.id}", f"B0", weight="distance")
                served += 1
            except:
                pass

        stats["served_users"].append(served)
        stats["time"].append(env.now)

        yield env.timeout(5)


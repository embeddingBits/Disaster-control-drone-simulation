import simpy
import numpy as np
from entities import Drone, User, BaseStation
from events import drone_process, traffic_process
from plots import plot_results

env = simpy.Environment()

# Base station
bs = BaseStation(0, (0, 0, 10))

# Drones
drones = [
    Drone(0, (50, 50, 60)),
    Drone(1, (200, 100, 60)),
    Drone(2, (100, 250, 60))
]

# Users
users = [
    User(i, (300 + i*20, 300 + i*10, 1.5))
    for i in range(6)
]

stats = {"time": [], "served_users": []}

# Drone missions
targets = [
    np.array((300, 300, 80)),
    np.array((350, 320, 80)),
    np.array((320, 350, 80))
]

for d, t in zip(drones, targets):
    env.process(drone_process(env, d, t, speed=5))

env.process(traffic_process(env, drones, users, [bs], stats))

env.run(until=250)

plot_results(stats)


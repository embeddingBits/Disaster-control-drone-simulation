import numpy as np

class Drone:
    def __init__(self, drone_id, pos, battery_j=10000):
        self.id = drone_id
        self.pos = np.array(pos, dtype=float)
        self.battery = battery_j
        self.alive = True

    def drain(self, amount):
        self.battery -= amount
        if self.battery <= 0:
            self.battery = 0
            self.alive = False


class User:
    def __init__(self, user_id, pos, demand_mbps=1.0):
        self.id = user_id
        self.pos = np.array(pos, dtype=float)
        self.demand = demand_mbps


class BaseStation:
    def __init__(self, bs_id, pos):
        self.id = bs_id
        self.pos = np.array(pos, dtype=float)


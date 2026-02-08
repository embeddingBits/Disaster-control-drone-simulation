import numpy as np

class Drone:
    def __init__(self, drone_id, area_size, battery=1000):
        self.id = drone_id
        self.pos = np.random.rand(2) * area_size
        self.battery = battery
        self.alive = True

    def move(self):
        if not self.alive:
            return
        self.pos += np.random.randn(2) * 2
        self.battery -= 1
        if self.battery <= 0:
            self.alive = False


class User:
    def __init__(self, area_size):
        self.pos = np.random.rand(2) * area_size
        self.detected = False
        self.served = False
        self.throughput = 0.0

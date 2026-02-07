import numpy as np

def move_towards(drone, target, speed, dt):
    direction = target - drone.pos
    dist = np.linalg.norm(direction)

    if dist < 1e-3:
        return

    step = min(speed * dt, dist)
    drone.pos += direction / dist * step


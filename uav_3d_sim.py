import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# =============================
# Simulation parameters
# =============================
NUM_DRONES = 3
NUM_USERS = 12
SIM_TIME = 200          # seconds
DT = 1                  # time step
DRONE_SPEED = 2.5       # m/s
DRONE_ALTITUDE = 80     # meters
COVERAGE_RADIUS = 120   # meters
BATTERY_INIT = 10000    # joules
BATTERY_DRAIN = 25      # J/s

# =============================
# Entities
# =============================
class Drone:
    def __init__(self, drone_id, pos):
        self.id = drone_id
        self.pos = np.array(pos, dtype=float)
        self.battery = BATTERY_INIT
        self.alive = True
        self.target = None

    def move(self):
        if not self.alive or self.target is None:
            return
        direction = self.target - self.pos
        dist = np.linalg.norm(direction)
        if dist < 1e-2:
            return
        step = min(DRONE_SPEED * DT, dist)
        self.pos += direction / dist * step

    def drain(self):
        self.battery -= BATTERY_DRAIN * DT
        if self.battery <= 0:
            self.battery = 0
            self.alive = False


class User:
    def __init__(self, uid, pos):
        self.id = uid
        self.pos = np.array(pos, dtype=float)
        self.served = False


# =============================
# Helper functions
# =============================
def distance(a, b):
    return np.linalg.norm(a - b)


def update_coverage(drones, users):
    for u in users:
        u.served = False
        for d in drones:
            if d.alive and distance(d.pos, u.pos) <= COVERAGE_RADIUS:
                u.served = True
                break


# =============================
# Initialization
# =============================

# Disaster zones (targets)
targets = [
    np.array([300, 300, DRONE_ALTITUDE]),
    np.array([450, 150, DRONE_ALTITUDE]),
    np.array([150, 450, DRONE_ALTITUDE]),
]

# Drones
drones = [
    Drone(0, [50, 50, DRONE_ALTITUDE]),
    Drone(1, [50, 450, DRONE_ALTITUDE]),
    Drone(2, [450, 50, DRONE_ALTITUDE]),
]

for d, t in zip(drones, targets):
    d.target = t

# Users (clustered in disaster zones)
users = []
uid = 0
for cx, cy in [(300,300), (450,150), (150,450)]:
    for _ in range(NUM_USERS // 3):
        users.append(User(uid, [cx + np.random.randn()*20,
                                 cy + np.random.randn()*20,
                                 0]))
        uid += 1

# =============================
# 3D Visualization
# =============================
fig = plt.figure(figsize=(9, 8))
ax = fig.add_subplot(111, projection='3d')

ax.set_xlim(0, 500)
ax.set_ylim(0, 500)
ax.set_zlim(0, 120)
ax.set_xlabel("X (m)")
ax.set_ylabel("Y (m)")
ax.set_zlabel("Z (m)")
ax.set_title("3D UAV Disaster Relief Network")

drone_scatter = ax.scatter([], [], [], c='red', s=80, label="Drones")
user_scatter = ax.scatter([], [], [], c='blue', s=20, label="Users")
served_scatter = ax.scatter([], [], [], c='green', s=30, label="Served Users")

ax.legend()

# =============================
# Animation step
# =============================
time_text = ax.text2D(0.02, 0.95, "", transform=ax.transAxes)

def update(frame):
    # Move & drain drones
    for d in drones:
        if d.alive:
            d.move()
            d.drain()

    # Update coverage
    update_coverage(drones, users)

    # Drone positions
    dx, dy, dz = zip(*[d.pos for d in drones if d.alive]) \
                 if any(d.alive for d in drones) else ([],[],[])

    # User positions
    ux = [u.pos[0] for u in users]
    uy = [u.pos[1] for u in users]
    uz = [u.pos[2] for u in users]

    sx = [u.pos[0] for u in users if u.served]
    sy = [u.pos[1] for u in users if u.served]
    sz = [u.pos[2] for u in users if u.served]

    drone_scatter._offsets3d = (dx, dy, dz)
    user_scatter._offsets3d = (ux, uy, uz)
    served_scatter._offsets3d = (sx, sy, sz)

    alive = sum(d.alive for d in drones)
    served = sum(u.served for u in users)

    time_text.set_text(
        f"t = {frame}s | Alive drones = {alive} | Users served = {served}/{len(users)}"
    )

    return drone_scatter, user_scatter, served_scatter, time_text


# =============================
# Run animation
# =============================
ani = FuncAnimation(fig, update,
                    frames=range(0, SIM_TIME, DT),
                    interval=80)

plt.show()


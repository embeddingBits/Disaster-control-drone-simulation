import numpy as np

def distance(a, b):
    return np.linalg.norm(a - b)

def los_probability(d):
    return np.exp(-d / 200)   # tunable

def link_capacity_mbps(d):
    if d == 0:
        return 1000
    pl = 20 * np.log10(d + 1)
    return max(0.5, 100 / (1 + pl))  # abstract rate


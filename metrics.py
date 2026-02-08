def compute_kpis(sim_result):
    users = sim_result["users"]
    drones = sim_result["drones"]

    total_users = len(users)
    served = sum(1 for u in users if u.served)
    detected = sum(1 for u in users if u.detected)

    avg_thr = sum(u.throughput for u in users if u.served) / max(1, served)

    return {
        "detection_rate": detected / total_users * 100,
        "service_rate": served / total_users * 100,
        "avg_throughput": avg_thr,
        "throughput_timeseries": sim_result["throughput_timeseries"],
        "alive_drones": sum(1 for d in drones if d.alive)
    }

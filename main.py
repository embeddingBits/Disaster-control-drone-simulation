from fastapi import FastAPI
from pydantic import BaseModel
from sim_core.simulation import run_simulation
from sim_core.metrics import compute_kpis

class ScenarioConfig(BaseModel):
    num_drones: int = 10
    num_users: int = 50
    area_size: float = 1000
    coverage_radius: float = 120
    search_radius: float = 200
    sim_time: int = 200
    battery_init: float = 1000

app = FastAPI(title="Drone Network Simulation API")

@app.post("/run")
def run_scenario(config: ScenarioConfig):
    sim_result = run_simulation(config)
    return compute_kpis(sim_result)

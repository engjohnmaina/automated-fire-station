import time
from config import state, runtime_config, state_lock
from engine import dijkstra, build_graph, get_bearing
from robot_client import send

def timeout_thread(loc):
    for i in range(runtime_config["timeout"], 0, -1):
        if not state["waiting_phone"]: return
        with state_lock:
            state["phone_timer"] = i
        time.sleep(1)
        
    with state_lock:
        if state["waiting_phone"]:
            state["waiting_phone"] = False
            state["jokers"] += 1
            fine = runtime_config["fine_first"] if state["jokers"] <= 2 else runtime_config["fine_after"]
            state["fine_total"] += fine
            state["fire"] = False

def return_seq(loc):
    time.sleep(1)
    send("pump/ON")
    time.sleep(2)
    send("pump/OFF")
    
    with state_lock:
        state["siren"] = False
        state["returning"] = True
        
    path, _ = dijkstra(loc, "STATION")
    with state_lock:
        state["path_to_home"] = path
        
    for i in range(len(path)-1):
        frm = path[i]
        to = path[i+1]
        GRAPH = build_graph()
        for nb, w, road in GRAPH[frm]:
            if nb == to:
                bearing, dx, dy, coords = get_bearing(frm, to)
                with state_lock:
                    state["target_bearing"] = bearing
                    state["coord"] = coords[to]["coord"]
                    state["angle_calc"] = f"dx={dx:.2f} dy={dy:.2f} {bearing}deg AUTO"
                    state["indicator"] = f"{road} {bearing}deg"
                send(f"turn/{bearing}")
                time.sleep(1)
                send(f"go/{to}")
                with state_lock:
                    state["robot_pos"] = to
                    state["dist"] += w
                time.sleep(w / runtime_config["speed_mps"] + 0.5)
                break
                
    with state_lock:
        state["robot_pos"] = "STATION"
        state["coord"] = "(0m,0m)"
        state["power_save"] = True
        state["indicator"] = "OFF"
        state["returning"] = False
        state["fire"] = False
    send("power/SAVE")

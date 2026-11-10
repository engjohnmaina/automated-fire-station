import threading
import time
import json
import os
from flask import Flask, request, jsonify, render_template
from config import runtime_config, state, state_lock, DEFAULT_SPEED_MPS, DEFAULT_STATION_TO_Y, DEFAULT_B1_FROM_Y, DEFAULT_B2_FROM_Y, DEFAULT_C1_FROM_B1, DEFAULT_C2_FROM_B2, DEFAULT_C_TO_E, DEFAULT_PID_KP, DEFAULT_PID_KI, DEFAULT_PID_KD
from engine import get_real_coords, get_bearing, build_graph, dijkstra
from robot_client import send
from sequences import timeout_thread, return_seq

app = Flask(__name__)
BACKUP_PATH = "config_backup.json"

def persist_config_to_disk():
    try:
        with open(BACKUP_PATH, "w") as f:
            json.dump(runtime_config, f)
    except Exception:
        pass

def load_persisted_config():
    if os.path.exists(BACKUP_PATH):
        try:
            with open(BACKUP_PATH, "r") as f:
                saved = json.load(f)
                runtime_config.update(saved)
        except Exception:
            pass

def verify_network_heartbeat_loop():
    while True:
        time.sleep(1)
        current_time = time.time()
        with state_lock:
            if current_time - state["last_heartbeat_time"] > 4.0:
                if state["robot_online"]:
                    state["robot_online"] = False
                    state["msg"] = "ALERT: Network Heartbeat Lost! Check robot Wi-Fi Access Point connection."
            else:
                state["robot_online"] = True

def evaluate_voltage_threshold_safety():
    current_v = state["robot_voltage"]
    cutoff_v = runtime_config["voltage_threshold"]
    
    max_v, min_v = 12.6, 11.1
    if current_v >= max_v: pct = 100
    elif current_v <= min_v: pct = 0
    else: pct = int(((current_v - min_v) / (max_v - min_v)) * 100)
    
    state["battery_percentage"] = pct

    if current_v < cutoff_v and not state["backup_battery_active"]:
        state["backup_battery_active"] = True
        state["msg"] = f"CRITICAL: Bus dropped to {current_v}V ({pct}%)! Below threshold {cutoff_v}V. Isolating power cell channels."
        send("relay/main/OFF")
        send("relay/backup/ON")
    elif current_v >= cutoff_v and state["backup_battery_active"]:
        state["backup_battery_active"] = False
        state["msg"] = "REGULAR: Main power rail restored safely."
        send("relay/backup/OFF")
        send("relay/main/ON")

@app.route("/")
def dash(): return render_template("dashboard.html")

@app.route("/api/status")
def api_status():
    evaluate_voltage_threshold_safety()
    coords = get_real_coords()
    curr = coords.get(state["robot_pos"], coords["STATION"])
    return jsonify({**state, "robot_speed": runtime_config["speed_mps"], "pid_kp": runtime_config["pid_kp"], "pid_ki": runtime_config["pid_ki"], "pid_kd": runtime_config["pid_kd"], "coord": curr["coord"], "voltage_threshold": runtime_config["voltage_threshold"]})

# NEW ADDITION: Station Reference Reset Hook Endpoint
@app.route("/api/reset_position", methods=["POST"])
def reset_position_reference():
    with state_lock:
        state["robot_pos"] = "STATION"
        state["coord"] = "(0m,0m)"
        state["dist"] = 0
        state["msg"] = "REFERENCE ALIGNED: System position calibrated back to Station home coordinates (0,0)."
    send("power/SAVE") # Pings the robot chip to cut power down to idle
    return jsonify({"status": "aligned"})

@app.route("/api/config")
def api_config_get(): return jsonify(runtime_config)

@app.route("/api/config/voltage", methods=["POST"])
def update_voltage_threshold():
    data = request.get_json() or {}
    val = data.get("voltage_threshold")
    if val is not None and val != "":
        with state_lock:
            runtime_config["voltage_threshold"] = float(val)
            state["msg"] = f"THRESHOLD SET - Safe boundary modified to {runtime_config['voltage_threshold']}V"
        persist_config_to_disk()
    return jsonify({"status": "success", "voltage_threshold": runtime_config["voltage_threshold"]})

@app.route("/api/config/update", methods=["POST"])
def api_config_update():
    data = request.get_json() or {}
    for key in ["speed_mps","station_to_y","b1_from_y","b2_from_y","c1_from_b1","c2_from_b2","c_to_e","pid_kp","pid_ki","pid_kd"]:
        val = data.get(key)
        if val is not None and val != "":
            try:
                num = float(val)
                if num > 0: runtime_config[key] = num
            except ValueError: pass
            
    for key in ["pid_max","pid_sample_ms","angle_tol"]:
        val = data.get(key)
        if val is not None and val != "":
            try: runtime_config[key] = int(val)
            except ValueError: pass
            
    with state_lock:
        state["msg"] = "CONFIG COMMITTED - Safe dictionary key mapping applied."
    persist_config_to_disk()
    return jsonify(runtime_config)

@app.route("/api/config/reset", methods=["POST"])
def api_config_reset():
    runtime_config.update({
        "speed_mps": DEFAULT_SPEED_MPS, "station_to_y": DEFAULT_STATION_TO_Y, "b1_from_y": DEFAULT_B1_FROM_Y,
        "b2_from_y": DEFAULT_B2_FROM_Y, "c1_from_b1": DEFAULT_C1_FROM_B1, "c2_from_b2": DEFAULT_C2_FROM_B2,
        "c_to_e": DEFAULT_C_TO_E, "pid_kp": DEFAULT_PID_KP, "pid_ki": DEFAULT_PID_KI, "pid_kd": DEFAULT_PID_KD,
        "max": 100, "sample_ms": 10, "angle_tol": 3, "voltage_threshold": 11.1
    })
    with state_lock:
        state["msg"] = "RESET OK - Volatile properties purged back to baseline defaults."
    persist_config_to_disk()
    return jsonify(runtime_config)

@app.route("/victim_fire")
def vf():
    loc = request.args.get("loc", "E")
    if time.time() - state["last_fire_time"] < runtime_config["cooldown"]: return "Cooldown", 429
    with state_lock:
        state["last_fire_time"] = time.time()
        state["fire_loc"] = loc
        state["fire"] = True
        state["waiting_phone"] = True
        state["phone_timer"] = runtime_config["timeout"]
    _, dx, dy, coords = get_bearing("STATION", loc)
    state["msg"] = f"FIRE SIGNAL AT {loc} {coords[loc]['coord']}. Confirm authorization stack..."
    threading.Thread(target=timeout_thread, args=(loc,), daemon=True).start()
    return "OK"

@app.route("/confirm/<ans>")
def confirm(ans):
    loc = request.args.get("loc", state["fire_loc"] or "E")
    if not state["waiting_phone"]: return "Already"
    with state_lock:
        state["waiting_phone"] = False
        
    if ans == "yes":
        path, d = dijkstra("STATION", loc)
        with state_lock:
            state["path_to_fire"] = path
            state["power_save"] = False
            state["siren"] = True
            state["dist"] = 0
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
                    send(f"turn/{bearing}")
                    time.sleep(1)
                    send(f"go/{to}")
                    with state_lock:
                        state["robot_pos"] = to
                        state["dist"] += w
                    time.sleep(w / runtime_config["speed_mps"] + 0.5)
                    break
        threading.Thread(target=return_seq, args=(loc,), daemon=True).start()
    else:
        with state_lock:
            state["victim_active"] = False
            state["fire"] = False
    return "OK"

@app.route("/register")
def reg():
    with state_lock:
        state["victim_active"] = True
        state["fire"] = False
        state["fire_loc"] = None
    return "OK"

@app.route("/compass/<int:heading>")
def comp(heading):
    v_val = request.args.get("v", default="12.6")
    with state_lock:
        state["current_bearing"] = heading
        state["robot_voltage"] = float(v_val)
        state["last_heartbeat_time"] = time.time()
        err = state["target_bearing"] - heading
        if err > 180: err -= 360
        if err < -180: err += 360
        state["pid_error"] = err
    return "OK"

@app.route("/update/<msg>")
def up(msg):
    if msg == "NO_FIRE_FOUND":
        with state_lock:
            loc = state["fire_loc"]
            state["jokers"] += 1
            fine = runtime_config["fine_first"] if state["jokers"] <= 2 else runtime_config["fine_after"]
            state["fine_total"] += fine
            state["victim_active"] = False
        threading.Thread(target=return_seq, args=(loc,), daemon=True).start()
    return "OK"

if __name__ == "__main__":
    load_persisted_config()
    threading.Thread(target=verify_network_heartbeat_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=80, debug=False)

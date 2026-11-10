import threading

DEFAULT_SPEED_MPS = 0.5
DEFAULT_STATION_TO_Y = 1.5
DEFAULT_B1_FROM_Y = 2.0
DEFAULT_B2_FROM_Y = 3.0
DEFAULT_C1_FROM_B1 = 2.0
DEFAULT_C2_FROM_B2 = 1.0
DEFAULT_C_TO_E = 2.0
DEFAULT_PID_KP = 2.0
DEFAULT_PID_KI = 0.1
DEFAULT_PID_KD = 0.5

# The Robot serves as the central Wi-Fi Router Gateway AP (192.168.4.1)
ROBOT_IP = "192.168.4.1"

# Safe global data wrapper locks to secure asynchronous updates
state_lock = threading.Lock()

runtime_config = {
    "speed_mps": DEFAULT_SPEED_MPS, "station_to_y": DEFAULT_STATION_TO_Y,
    "b1_from_y": DEFAULT_B1_FROM_Y, "b2_from_y": DEFAULT_B2_FROM_Y,
    "c1_from_b1": DEFAULT_C1_FROM_B1, "c2_from_b2": DEFAULT_C2_FROM_B2,
    "c_to_e": DEFAULT_C_TO_E, "pid_kp": DEFAULT_PID_KP, "pid_ki": DEFAULT_PID_KI,
    "pid_kd": DEFAULT_PID_KD, "pid_max": 100, "pid_sample_ms": 10, "angle_tol": 3,
    "fine_first": 2000, "fine_after": 5000, "timeout": 60, "cooldown": 30,
    "voltage_threshold": 11.1
}

PIXEL_POS = {
    "STATION": {"x": 40, "y": 180}, "A": {"x": 110, "y": 180},
    "B1": {"x": 250, "y": 60}, "B2": {"x": 250, "y": 300},
    "C1": {"x": 410, "y": 60}, "C2": {"x": 410, "y": 300}, "E": {"x": 560, "y": 180}
}

state = {
    "robot_pos": "STATION", "fire_loc": None, "path_to_fire": ["STATION"], "path_to_home": ["STATION"],
    "siren": False, "indicator": "OFF", "dist": 0, "fire": False, "victim_active": True,
    "power_save": True, "msg": "READY - Robot Access Point active. Monitoring grid channels...",
    "fine_total": 0, "jokers": 0, "returning": False, "waiting_phone": False, "phone_timer": 0, "last_fire_time": 0,
    "target_bearing": 0, "current_bearing": 0, "pid_error": 0,
    "coord": "(0m,0m)", "angle_calc": "atan2 auto",
    "robot_voltage": 12.6,
    "battery_percentage": 100,
    "backup_battery_active": False,
    "robot_online": False,       # Live competition heartbeat tracking variable
    "last_heartbeat_time": 0     # Internal reference epoch timestamp
}

import threading
import requests
from config import ROBOT_IP

def outbound_worker(cmd, target_ip):
    try: 
        requests.get(f"http://{target_ip}/{cmd}", timeout=0.4)
    except Exception: 
        pass

def send(cmd):
    # Offloads outbox commands instantly to a non-blocking daemon thread
    threading.Thread(target=outbound_worker, args=(cmd, ROBOT_IP), daemon=True).start()

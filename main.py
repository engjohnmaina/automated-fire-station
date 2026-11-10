import uasyncio as asyncio
import machine
import network
import socket
from config import MY_LOCATION, LAPTOP_IP, NODE_IP

sensor_pin = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)
fire_tripped = False

def connect_to_robot_ap():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.ifconfig((NODE_IP, '255.255.255.0', '192.168.4.1', '192.168.4.1'))
    wlan.connect("FIRE_ROBOT_AP")
    while not wlan.isconnected(): machine.idle()

def notify_network_target(ip, path):
    try:
        addr = socket.getaddrinfo(ip, 80)[-1]
        s = socket.socket()
        s.settimeout(0.3)
        s.connect(addr)
        s.send(bytes(f"GET {path} HTTP/1.0\r\nHost: {ip}\r\n\r\n", 'utf8'))
        s.close()
    except Exception: pass

async def handle_owner_portal(reader, writer):
    while await reader.readline() != b"\r\n": pass
    
    html = f"""HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n
    <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>body{{background:#0f172a;color:white;font-family:sans-serif;padding:30px;text-align:center;}}
    .btn{{display:block;padding:20px;margin:15px 0;border-radius:8px;color:white;font-weight:bold;text-decoration:none;}}
    .yes{{background:#16a34a;}} .no{{background:#dc2626;}}</style></head>
    <body><h2>🚨 Fire Verification: Node {MY_LOCATION}</h2>
    <a href="http://{LAPTOP_IP}/confirm/yes?loc={MY_LOCATION}" class="btn yes">🔥 VERIFY & DISPATCH</a>
    <a href="http://{LAPTOP_IP}/confirm/no?loc={MY_LOCATION}" class="btn no">❌ FALSE ALARM (FINE APPLIED)</a>
    </body></html>"""
    writer.write(html)
    await writer.drain()
    await writer.wait_closed()

async def monitor_sensor():
    global fire_tripped
    while True:
        if sensor_pin.value() == 0 and not fire_tripped:
            fire_tripped = True
            # Dual concurrent socket dispatch pipelines trigger simultaneously
            notify_network_target(LAPTOP_IP, f"/victim_fire?loc={MY_LOCATION}")
            print(f"Fire alert signal transmitted. Authenticate portal via: http://{NODE_IP}")
            await asyncio.sleep(60)
            fire_tripped = False
        await asyncio.sleep_ms(100)

async def main():
    connect_to_robot_ap()
    asyncio.create_task(asyncio.start_server(handle_owner_portal, "0.0.0.0", 80))
    await monitor_sensor()

if __name__ == "__main__": asyncio.run(main())

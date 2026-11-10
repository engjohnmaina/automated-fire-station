import math
import heapq
from config import runtime_config, PIXEL_POS, DEFAULT_B1_FROM_Y, DEFAULT_B2_FROM_Y

def get_real_coords():
    st_y = runtime_config["station_to_y"]
    b1 = runtime_config["b1_from_y"]
    b2 = runtime_config["b2_from_y"]
    c1 = runtime_config["c1_from_b1"]
    c2 = runtime_config["c2_from_b2"]
    ce = runtime_config["c_to_e"]
    lateral = 2.1
    coords = {}
    coords["STATION"] = {"real_x": 0.0, "real_y": 0.0, "coord": "(0m,0m)"}
    coords["A"] = {"real_x": st_y, "real_y": 0.0, "coord": f"({st_y}m,0m)"}
    coords["B1"] = {"real_x": st_y + b1 * 0.85, "real_y": -lateral * (b1 / DEFAULT_B1_FROM_Y), "coord": f"({st_y + b1 * 0.85:.1f}m,{-lateral * (b1 / DEFAULT_B1_FROM_Y):.1f}m)"}
    coords["B2"] = {"real_x": st_y + b2 * 0.85, "real_y": lateral * (b2 / DEFAULT_B2_FROM_Y), "coord": f"({st_y + b2 * 0.85:.1f}m,{lateral * (b2 / DEFAULT_B2_FROM_Y):.1f}m)"}
    coords["C1"] = {"real_x": coords["B1"]["real_x"] + c1, "real_y": coords["B1"]["real_y"], "coord": f"({coords['B1']['real_x'] + c1:.1f}m,{coords['B1']['real_y']:.1f}m)"}
    coords["C2"] = {"real_x": coords["B2"]["real_x"] + c2, "real_y": coords["B2"]["real_y"], "coord": f"({coords['B2']['real_x'] + c2:.1f}m,{coords['B2']['real_y']:.1f}m)"}
    avg_x = (coords["C1"]["real_x"] + coords["C2"]["real_x"]) / 2
    coords["E"] = {"real_x": avg_x + ce * 0.6, "real_y": 0.0, "coord": f"({avg_x + ce * 0.6:.1f}m,0m)"}
    for k in PIXEL_POS:
        coords[k]["x"] = PIXEL_POS[k]["x"]
        coords[k]["y"] = PIXEL_POS[k]["y"]
        coords[k]["name"] = k
    return coords

def get_bearing(frm, to):
    coords = get_real_coords()
    dx = coords[to]["real_x"] - coords[frm]["real_x"]
    dy = coords[to]["real_y"] - coords[frm]["real_y"]
    ang = math.degrees(math.atan2(dx, -dy))
    if ang < 0: ang += 360
    return int(ang), dx, dy, coords

def build_graph():
    return {
        "STATION": [("A", runtime_config["station_to_y"], "EXIT_ROAD")],
        "A": [("B1", runtime_config["b1_from_y"], "EAST_ROAD_1"), ("B2", runtime_config["b2_from_y"], "EAST_ROAD_2"), ("STATION", runtime_config["station_to_y"], "WEST_EXIT")],
        "B1": [("C1", runtime_config["c1_from_b1"], "EAST_ROAD_1"), ("C2", 3, "DIAGONAL_1"), ("A", runtime_config["b1_from_y"], "WEST_ROAD_1")],
        "B2": [("C2", runtime_config["c2_from_b2"], "EAST_ROAD_2"), ("C1", 3, "DIAGONAL_2"), ("A", runtime_config["b2_from_y"], "WEST_ROAD_2")],
        "C1": [("E", runtime_config["c_to_e"], "EAST_ROAD_1"), ("B1", runtime_config["c1_from_b1"], "WEST_ROAD_1"), ("B2", 3, "DIAGONAL_2")],
        "C2": [("E", runtime_config["c_to_e"], "EAST_ROAD_2"), ("B2", runtime_config["c2_from_b2"], "WEST_ROAD_2"), ("B1", 3, "DIAGONAL_1")],
        "E": [("C1", runtime_config["c_to_e"], "WEST_ROAD_1"), ("C2", runtime_config["c_to_e"], "WEST_ROAD_2")]
    }

def dijkstra(start, end):
    GRAPH = build_graph()
    pq = [(0, start, [])]; vis = {}
    while pq:
        d, n, p = heapq.heappop(pq)
        if n in vis: continue
        vis[n] = d; p = p + [n]
        if n == end: return p, d
        for nb, w, road in GRAPH.get(n, []):
            if nb not in vis: heapq.heappush(pq, (d + w, nb, p))
    return [start, end], 

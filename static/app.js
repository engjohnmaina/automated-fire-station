const PIXEL_POS = {
  STATION: { x: 40, y: 180, name: "Home Base Station" },
  A: { x: 120, y: 180, name: "Alpha Corridor Node" },
  B1: { x: 260, y: 70, name: "Junction B1 East" },
  B2: { x: 260, y: 290, name: "Junction B2 East" },
  C1: { x: 420, y: 70, name: "Transit C1 Pipeline" },
  C2: { x: 420, y: 290, name: "Transit C2 Pipeline" },
  E: { x: 550, y: 180, name: "Terminal Market E" },
};

// Map tracks connecting all node paths directly
const TOPOLOGY = {
  STATION: ["A"],
  A: ["B1", "B2", "STATION"],
  B1: ["C1", "C2", "A"],
  B2: ["C2", "C1", "A"],
  C1: ["E", "B1", "B2"],
  C2: ["E", "B2", "B1"],
  E: ["C1", "C2"],
};

const mapCanvas = document.getElementById("mapWorkspace");

Object.keys(PIXEL_POS).forEach((key) => {
  const data = PIXEL_POS[key];
  const div = document.createElement("div");
  div.className = "node";
  div.id = `node_${key}`;
  div.style.left = `${data.x}px`;
  div.style.top = `${data.y}px`;
  div.innerHTML = `${key}<div class="lbl">${data.name}</div>`;
  mapCanvas.appendChild(div);
});

function updatePathways(activePath = []) {
  document.querySelectorAll(".road").forEach((el) => el.remove());
  Object.keys(TOPOLOGY).forEach((srcKey) => {
    TOPOLOGY[srcKey].forEach((destKey) => {
      const src = PIXEL_POS[srcKey];
      const dest = PIXEL_POS[destKey];
      if (!src || !dest) return;

      const x1 = src.x + 22,
        y1 = src.y + 22;
      const x2 = dest.x + 22,
        y2 = dest.y + 22;

      const distance = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
      const inclination = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;

      let isHighlighted = false;
      const srcIdx = activePath.indexOf(srcKey);
      const destIdx = activePath.indexOf(destKey);
      if (srcIdx !== -1 && destIdx !== -1 && Math.abs(srcIdx - destIdx) === 1) {
        isHighlighted = true;
      }

      const road = document.createElement("div");
      road.className = `road ${isHighlighted ? "highlight" : ""}`;
      road.style.width = `${distance}px`;
      road.style.left = `${x1}px`;
      road.style.top = `${y1}px`;
      road.style.transform = `rotate(${inclination}deg)`;
      mapCanvas.appendChild(road);
    });
  });
}

function synchronizeSystemTelemetry() {
  fetch("/api/status")
    .then((res) => res.json())
    .then((data) => {
      document.getElementById("val_pos").innerText = data.robot_pos;
      document.getElementById("val_coord").innerText = data.coord;
      document.getElementById("val_bearing").innerText =
        `${data.target_bearing}° / ${data.current_bearing}°`;
      document.getElementById("val_pid_err").innerText = `${data.pid_error}°`;
      document.getElementById("val_odo").innerText =
        `${data.dist.toFixed(2)}m | Jokers: ${data.jokers}/3`;
      document.getElementById("val_siren").innerText =
        `${data.siren ? "🚨 ON" : "OFF"} | KSH ${data.fine_total}`;
      document.getElementById("val_voltage").innerText =
        `${data.robot_voltage.toFixed(2)} V`;
      document.getElementById("sysMsg").innerText = data.msg;

      const hb = document.getElementById("hbCard");
      const onlineText = document.getElementById("val_online");
      if (data.robot_online) {
        onlineText.innerText = "CONNECTED";
        hb.className = "tel-item online";
      } else {
        onlineText.innerText = "DISCONNECTED";
        hb.className = "tel-item offline";
      }

      document.getElementById("sirenCard").className = data.siren
        ? "tel-item active-siren"
        : "tel-item";
      document.getElementById("batFill").style.width =
        `${data.battery_percentage}%`;
      document.getElementById("batTxt").innerText =
        `${data.battery_percentage}%`;
      document.getElementById("batFill").style.backgroundColor =
        data.backup_battery_active ? "#eab308" : "#22c55e";

      if (data.waiting_phone) {
        document.getElementById("phoneConfirmContainer").style.display =
          "block";
        document.getElementById("lbl_phone_timer").innerText = data.phone_timer;
      } else {
        document.getElementById("phoneConfirmContainer").style.display = "none";
      }

      document
        .querySelectorAll(".node")
        .forEach((node) => node.classList.remove("active", "fire-active"));
      const currentActiveNode = document.getElementById(
        `node_${data.robot_pos}`,
      );
      if (currentActiveNode) currentActiveNode.classList.add("active");

      if (data.fire && data.fire_loc) {
        const fireNode = document.getElementById(`node_${data.fire_loc}`);
        if (fireNode) fireNode.classList.add("fire-active");
      }

      const currentActiveTrack = data.returning
        ? data.path_to_home
        : data.path_to_fire;
      updatePathways(currentActiveTrack);
    })
    .catch(() => {
      document.getElementById("sysMsg").innerText =
        "CRITICAL: Dashboard communication link severed.";
    });
}

function pullActiveConfigurations() {
  fetch("/api/config")
    .then((res) => res.json())
    .then((cfg) => {
      document.getElementById("input_v_thresh").value = cfg.voltage_threshold;
      const inputs = document.querySelectorAll("input[type='number']");
      inputs.forEach((input) => {
        if (cfg[input.name] !== undefined) {
          input.value = cfg[input.name];
        }
      });
    });
}

function postForm(formId, targetEndpoint, payloadFunc) {
  document.getElementById(formId).addEventListener("submit", function (e) {
    e.preventDefault();
    fetch(targetEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payloadFunc()),
    })
      .then((res) => res.json())
      .then(() => synchronizeSystemTelemetry());
  });
}

postForm("distanceForm", "/api/config/update", () =>
  Object.fromEntries(
    new FormData(document.getElementById("distanceForm")).entries(),
  ),
);
postForm("pidForm", "/api/config/update", () =>
  Object.fromEntries(
    new FormData(document.getElementById("pidForm")).entries(),
  ),
);

postForm("voltageForm", "/api/config/voltage", () => {
  return {
    voltage_threshold: parseFloat(
      document.getElementById("input_v_thresh").value,
    ),
  };
});

function postConfirmation(status) {
  fetch(`/confirm/${status}`).then(() => {
    document.getElementById("phoneConfirmContainer").style.display = "none";
    synchronizeSystemTelemetry();
  });
}

function triggerPositionReset() {
  if (confirm("Force align coordinates reference frame back to (0,0)?")) {
    fetch("/api/reset_position", { method: "POST" }).then(() =>
      synchronizeSystemTelemetry(),
    );
  }
}

function triggerConfigReset() {
  if (
    confirm(
      "Reset layout system configuration attributes back to factory baseline defaults?",
    )
  ) {
    fetch("/api/config/reset", { method: "POST" }).then(() =>
      pullActiveConfigurations(),
    );
  }
}

function triggerNodeRegister() {
  fetch("/register").then(() => synchronizeSystemTelemetry());
}

pullActiveConfigurations();
updatePathways();
setInterval(synchronizeSystemTelemetry, 500);

"""Heartbeat agent. Run on every bare-metal/VM node (systemd service or k8s DaemonSet).

Requires only `psutil`. Configuration via environment:
  PGS_API_URL      e.g. http://api.pgs.internal:8000
  PGS_AGENT_TOKEN  shared secret, must match the API's PGS_AGENT_TOKEN
  PGS_NODE_ID      unique id, e.g. "k8s-worker-2" (default: hostname)
  PGS_NODE_ROLE    e.g. "control-plane", "worker", "storage", "crawler"
  PGS_INTERVAL_S   seconds between heartbeats (default 15)
"""

import json
import os
import socket
import time
import urllib.error
import urllib.request

import psutil


def read_metrics() -> dict[str, object]:
    boot = psutil.boot_time()
    return {
        "node_id": os.environ.get("PGS_NODE_ID", socket.gethostname()),
        "hostname": socket.gethostname(),
        "role": os.environ.get("PGS_NODE_ROLE", "worker"),
        "ip_address": os.environ.get("PGS_NODE_IP"),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "load_1m": psutil.getloadavg()[0],
        "cpu_count": psutil.cpu_count() or 1,
        "uptime_seconds": int(time.time() - boot),
    }


def send(url: str, token: str, payload: dict[str, object]) -> None:
    request = urllib.request.Request(
        f"{url.rstrip('/')}/api/v1/admin/monitoring/nodes/heartbeat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Agent-Token": token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5):
        pass


def main() -> None:
    url = os.environ["PGS_API_URL"]
    token = os.environ["PGS_AGENT_TOKEN"]
    interval = float(os.environ.get("PGS_INTERVAL_S", "15"))
    while True:
        try:
            send(url, token, read_metrics())
        except (urllib.error.URLError, TimeoutError) as exc:
            # Keep going: the API being briefly unreachable must not kill the agent.
            print(f"heartbeat failed: {exc}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
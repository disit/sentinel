import subprocess
import json

nodes_output = subprocess.run(
    ["kubectl", "get", "nodes", "-o", "json"],
    capture_output=True,
    text=True
)
nodes_data = json.loads(nodes_output.stdout)

# Get pods JSON (across all namespaces)
pods_output = subprocess.run(
    ["kubectl", "get", "pods", "-A", "-o", "json"],
    capture_output=True,
    text=True
)
pods_data = json.loads(pods_output.stdout)

# Count running pods per node
pod_counts = {}
for pod in pods_data["items"]:
    node_name = pod.get("spec", {}).get("nodeName")
    pod_phase = pod.get("status", {}).get("phase")
    if node_name and pod_phase == "Running":
        pod_counts[node_name] = pod_counts.get(node_name, 0) + 1

# Construct final node info with pod counts
node_info = []
for item in nodes_data["items"]:
    name = item["metadata"]["name"]
    capacity = item["status"]["capacity"]
    allocatable = item["status"]["allocatable"]

    node_data = {
        "name": name,
        "capacity": {
            "cpu": capacity.get("cpu"),
            "memory": capacity.get("memory")
        },
        "running_pods": f"{str(pod_counts.get(name, 0))}/{capacity.get('pods')}",
        "status": ", ".join(["Ready" if a["message"] == "kubelet is posting ready status" else a["message"] for a in item["status"]["conditions"] if a["status"]=="True"])
    }

    node_info.append(node_data)

# Save to JSON file
with open("nodes.json", "w") as f:
    json.dump(node_info, f, indent=2)

# Print to console
print(json.dumps(node_info))

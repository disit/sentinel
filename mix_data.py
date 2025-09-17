import json
import subprocess

containers_ps = [a for a in (subprocess.run('docker ps --format json -a', shell=True, capture_output=True, text=True, encoding="utf_8").stdout).split('\n')][:-1]
containers_stats = [b for b in (subprocess.run('docker stats --format json -a --no-stream', shell=True, capture_output=True, text=True, encoding="utf_8").stdout).split('\n')][:-1]
containers_merged = []
for container_stats in containers_stats:
    for container_ps in containers_ps:
        for key1, value1 in json.loads(container_stats).items():
            for key2, value2 in json.loads(container_ps).items():
                if key1 == "Name" and key2 == "Names":
                    if value1 == value2:
                        containers_merged.append({**json.loads(container_ps), **json.loads(container_stats)})

print(containers_merged[0].keys())
for current in containers_merged:
    td = {}

    td["Command"] = current["Command"]
    td["CreatedAt"] = current["CreatedAt"]
    td["ID"] = current["ID"]
    td["Image"] = current["Image"]
    td["Labels"] = current["Labels"]
    td["Mounts"] = current["Mounts"]
    td["Names"] = current["Names"]
    td["Name"] = current["Names"]
    td["Ports"] = current["Ports"]
    td["RunningFor"] = current["RunningFor"]
    td["State"] = current["State"]
    td["Status"] = current["Status"]
    td["Container"] = current["Container"]
    # host origin = node, sorta
    td["Node"] = "host" #current[""]
    td["Volumes"] = current["LocalVolumes"]
    td["Namespace"] = "'Docker'"

    print(json.dumps(td))
    print("\n"+"="*20+"\n")
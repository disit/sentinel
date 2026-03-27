import json
from datetime import datetime
import copy
imported = json.load(open("json.json"))

for item in imported["items"]:
    conversion = {}
    try:
        command = item.get("command", [])
        args = item.get("args", [])
        full_command = command + args
        if full_command:
            conversion["Command"] = full_command
    except Exception as E: # no command set, read from image
        #conversion["Command"] = subprocess.run(f"kubectl exec {item['metadata']['name']} -n {namespace} -- cat /proc/1/cmdline | tr '\0' ' '", shell=True, capture_output=True, text=True, encoding="utf_8").stdout
        conversion["Command"] = "Command not found"
    conversion["Source"]="Qui"
    conversion["CreatedAt"] = item["metadata"]["creationTimestamp"]
    conversion["ID"] = item["metadata"]["uid"]
    conversion["Image"] = item["spec"]["containers"][0]["image"]
    try:
        conversion["Labels"] = ", ".join([f"{label}: {value}" for label, value in item["metadata"]["labels"].items()])
    except KeyError:
        conversion["Labels"] = "No labels"
    try:
        conversion["Mounts"] = ", ".join([f"{a['mountPath']}: {a['name']}" for a in item["spec"]["containers"][0]["volumeMounts"]])
    except KeyError:
        conversion["Mounts"] = "No volumes"
    conversion["Names"] = item["metadata"]["name"]
    try:
        conversion["Ports"] = ", ".join([f"{a['containerPort']}" for a in item["spec"]["containers"][0]["ports"]])
    except KeyError as E:
        conversion["Ports"] = "No ports"

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        dt1 = datetime.strptime(item["status"]["containerStatuses"][0]["state"]["running"]["startedAt"], fmt)
        dt2 = datetime.now()
        conversion["RunningFor"] = f"{(dt2-dt1).days} day(s), {(dt2-dt1).seconds // 3600} hour(s), {((dt2-dt1).seconds % 3600) // 60} minute(s) and {(dt2-dt1).seconds % 60} second(s)"
    except Exception as E:
        conversion["RunningFor"] = "Not running"
    conversion["State"] = list(item["status"]["containerStatuses"][0]["state"].keys())[0] + " - restarts: " + str(item["status"]["containerStatuses"][0]["restartCount"])
    conversion["Status"] = item["status"]["conditions"][0]["type"] # actually a list, has the last few different statuses
    try:
        conversion["Container"] = item["status"]["containerStatuses"][0]["containerID"][item["status"]["containerStatuses"][0]["containerID"].find("://")+3:]
    except:
        conversion["Container"] = "No container id found!"
    conversion["Name"] = item["metadata"]["name"]

    # new things
    conversion["Node"] = item["spec"]["nodeName"]
    try:
        temp_vols=copy.deepcopy(item["spec"]["volumes"])
        temp_str = ""
        for vol_num in range(len(item["spec"]["volumes"])):
            temp_str += f"{item['spec']['volumes'][vol_num]['name']}: "
            del temp_vols[vol_num]["name"]
            temp_str += str(list(temp_vols[vol_num].keys())[0]) + ", "

        conversion["Volumes"] = temp_str
    except KeyError:
        conversion["Volumes"] = "No volumes"
    conversion["Namespace"] = item["metadata"]["namespace"]
    print(conversion["Container"])
        

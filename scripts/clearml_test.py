import json
import datetime
import sys
import requests
from requests.auth import HTTPBasicAuth

## todo error proof

ACCESS_KEY= sys.argv[1]
SECRET_KEY= sys.argv[2]

url = "http://192.168.1.52:8008/auth.login"


response = requests.request("GET", url, auth=HTTPBasicAuth(ACCESS_KEY, SECRET_KEY))
if response.status_code != 200:
    sys.stderr.write(f"Couldn't get token from clearml\n")
    exit(-1)

TOKEN = json.loads(response.text)["data"]["token"]


url_2 = "http://192.168.1.52:8008/workers.get_all"

headers = {
  'Authorization': f'Bearer {TOKEN}',
  'Content-Type': 'application/json'
}

response_2 = requests.request("POST", url_2, headers=headers)
if response_2.status_code != 200:
    sys.stderr.write(f"Couldn't read clearml hosts status from clearml health endpoint\n")
    exit(-1)
    


hosts = {"192.168.1.41", "192.168.1.13", "192.168.1.182", "192.168.0.175", "192.168.1.183", "192.168.1.181", "192.168.1.61", "192.168.1.42", "192.168.0.57"}
og = json.loads(response_2.text)
for w in og["data"]["workers"]:
    if w["ip"] in hosts:
        hosts.remove(w["ip"])
    else:
        sys.stderr.write(f"It seems that {w['ip']} infiltrated the clearml cluster?\n")
    provided_time = datetime.datetime.fromisoformat(w["last_activity_time"])

    current_time = datetime.datetime.now(datetime.timezone.utc)

    time_diff = current_time - provided_time
    if time_diff.seconds>90:
        sys.stderr.write(f"{w['ip']} was alive {time_diff.seconds} seconds(s) ago")
    else:
        print(f"{w['ip']} was alive {time_diff.seconds} second(s) ago")
for left_w in hosts:
    sys.stderr.write(f"I didn't find {left_w}!\n")
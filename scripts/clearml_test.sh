#!/bin/bash

# --- CONFIGURATION ---
CLEARML_API="http://192.168.1.52:8008"
ACCESS_KEY="YOUR_ACCESS_KEY"
SECRET_KEY="YOUR_SECRET_KEY"

# 1. Get Authentication Token
TOKEN_RESPONSE=$(curl -s -u "$ACCESS_KEY:$SECRET_KEY" "$CLEARML_API/auth.login")
TOKEN=$(echo "$TOKEN_RESPONSE" | grep -oP '"token":\s*"\K[^"]+')

if [ -z "$TOKEN" ]; then
    # Print auth error to stderr
    echo "Error: Could not authenticate. Check your credentials." >&2
    exit 1
fi


# 2. Query and Filter
# Double heredoc first makes the code with the json within it, then runs it into python
curl -s -X POST "$CLEARML_API/workers.get_all" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{}' | python3 <(cat <<'EOF'
import json
import datetime
import sys

hosts = {"192.168.1.41", "192.168.1.13", "192.168.1.182", "192.168.0.175", "192.168.1.183", "192.168.1.181", "192.168.1.61", "192.168.1.42", "192.168.0.57"}
og_msg = sys.stdin.read()
og = json.loads(og_msg)
for w in og["data"]["workers"]:
    if w["ip"] in hosts:
        hosts.remove(w["ip"])
    else:
        sys.stderr.write(f"It seems that {w['ip']} infiltrated the clearml cluster?\n")
    provided_time = datetime.datetime.fromisoformat(w["last_activity_time"])

    # 3. Get the current time (UTC)
    current_time = datetime.datetime.now(datetime.timezone.utc)

    # 4. Compare them
    time_diff = current_time - provided_time
    if time_diff.seconds>90:
        sys.stderr.write(f"{w['ip']} was alive {time_diff.seconds} seconds(s) ago")
    else:
        print(f"{w['ip']} was alive {time_diff.seconds} second(s) ago")
for left_w in hosts:
    sys.stderr.write(f"I didn't find {left_w}!\n")
EOF
)
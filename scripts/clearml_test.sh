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
curl -s -X POST "$CLEARML_API/workers.get_all" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{}' | python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    workers = data.get('data', {}).get('workers', [])
except Exception as e:
    sys.stderr.write(f'Error parsing JSON: {e}\n')
    sys.exit(1)

down_count = 0
for w in workers:
    status = w.get('status', 'unknown')
    worker_id = w.get('id', 'unknown')
    ip = w.get('ip', 'unknown')
    
    if status == 'offline':
        # Directing specific worker errors to stderr
        sys.stderr.write(f'[DOWN] Agent: {worker_id} (IP: {ip})\n')
        down_count += 1

if down_count == 0:
    print('Status: All agents healthy.')
else:
    sys.stderr.write(f'Total Agents Down: {down_count}\n')
    sys.exit(1)
"
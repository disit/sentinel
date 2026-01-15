#!/bin/bash

# Parameter Mapping
# $1: Host (e.g., 127.0.0.1)
# $2: Port (e.g., 9080)
# $3: Timeout (Defaults to 10 if not provided)
HOST=$1
PORT=$2
TIMEOUT=${3:-10}

# Basic validation to ensure Host and Port are provided
if [ -z "$HOST" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <host> <port> [timeout]" >&2
    exit 1
fi

# Execute netcat
# -z: Scan for listening daemons without sending data
# -n: Skip DNS resolution
# -w: Specifies the timeout for connects and final net reads
nc -zn -w "$TIMEOUT" "$HOST" "$PORT" > /dev/null 2>&1

# Check the exit status of the nc command
if [ $? -eq 0 ]; then
    echo "ok"
else
    echo "error: connection refused or timeout" >&2
    exit 1
fi
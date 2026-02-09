#!/bin/bash

# Parameter Mapping
HOST=$1
PORT=$2
TIMEOUT=${3:-10}
RERTIES=${4:-3}
RETRIES_TIMEOUT=${5:-10}

# Basic validation to ensure Host and Port are provided
if [ -z "$HOST" ] || [ -z "$PORT" ]; then
    echo "Usage: $0 <host> <port> [timeout] [retries]" >&2
    exit 1
fi

TOTAL_LOG=""

for ((i=1; i<=RETRIES; i++)); do
    # Capture both stdout and stderr (2>&1) into the variable OUTPUT
    OUTPUT=$(nc -zn -w "$TIMEOUT" "$HOST" "$PORT" > /dev/null 2>&1)
    EXIT_STATUS=$?

    if [ $EXIT_STATUS -eq 0 ]; then
        # Success! Print only the current output to stdout and exit
        echo "ok"
        exit 0
    fi

    # Record failure details for later
    TOTAL_LOG+="Attempt $i: $OUTPUT"$'\n'

    if [ "$i" -lt "$RETRIES" ]; then
        echo "Attempt #$i failed, trying until $RETRIES total retries"
        sleep $RETRIES_TIMEOUT
    fi
done

# If we've exhausted retries, dump the entire history to stderr
echo -e "$TOTAL_LOG" >&2
exit 1

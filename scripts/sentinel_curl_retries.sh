#!/bin/bash

URL=$1
TIMEOUT=${2:-10}
RETRIES=${3:-3}

if [ -z "$URL" ]; then
    echo "Usage: $0 <url> [timeout] [retries]" >&2
    exit 1
fi

# Track the output of all attempts for the final error report
TOTAL_LOG=""

for ((i=1; i<=RETRIES; i++)); do
    # Capture both stdout and stderr (2>&1) into the variable OUTPUT
    OUTPUT=$(curl -ILsSf --max-time "$TIMEOUT" "$URL" -o /dev/null -w "%{http_code}" 2>&1)
    EXIT_STATUS=$?

    if [ $EXIT_STATUS -eq 0 ]; then
        # Success! Print only the current output to stdout and exit
        echo "Output: $OUTPUT"
        exit 0
    fi

    # Record failure details for later
    TOTAL_LOG+="Attempt $i: $OUTPUT"$'\n'

    if [ "$i" -lt "$RETRIES" ]; then
        echo "Attempt #$i failed, trying until $RETRIES"
        sleep 1
    fi
done

# If we've exhausted retries, dump the entire history to stderr
echo -e "$TOTAL_LOG" >&2
exit 1

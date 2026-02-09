#!/bin/bash

URL=$1
EXPECTED_CODE=$2
TIMEOUT=${3:-10}
RETRIES=${4:-3}
RETRIES_TIMEOUT=${5:-10}

if [ -z "$URL" ]; then
    echo "Usage: $0 <url> [timeout] [retries]" >&2
    exit 1
fi

# Track the output of all attempts for the final error report
TOTAL_LOG=""

for ((i=1; i<=RETRIES; i++)); do
    # Capture both stdout and stderr (2>&1) into the variable OUTPUT
    OUTPUT=$(curl -sL --max-time "$TIMEOUT" -o /dev/null -w "%{http_code}" "$URL" 2>&1)
    EXIT_STATUS=$?

    if [ $EXIT_STATUS -eq 0 ]; then
        # Success! Print only the current output to stdout and exit
        if [ "$OUTPUT" == "000" ]; then
            TOTAL_LOG+="Attempt $i: $OUTPUT"$'\n'
        elif [ "$OUTPUT" -eq "$EXPECTED_CODE" ]; then
            echo "ok"
            exit 0
        else
            TOTAL_LOG+="Attempt $i: $OUTPUT"$'\n'
        fi
    fi

    # Record failure details for later
    TOTAL_LOG+="Attempt $i: $OUTPUT"$'\n'

    if [ "$i" -lt "$RETRIES" ]; then
        echo "Attempt #$i failed, trying until $RETRIES total retries"
        sleep $RETRIES_TIMEOUT
    fi
done

# If we've exhausted retries, dump the entire history to stderr
echo "error: status $OUTPUT (expected $EXPECTED_CODE)" >&2
exit 1
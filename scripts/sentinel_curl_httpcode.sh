#!/bin/bash

# Parameter Mapping
# $1: URL
# $2: Expected HTTP Status Code (e.g., 200, 302, 401)
# $3: Timeout (Defaults to 10)
URL=$1
EXPECTED_CODE=$2
TIMEOUT=${3:-10}

# Validation: Ensure URL and Expected Code are provided
if [ -z "$URL" ] || [ -z "$EXPECTED_CODE" ]; then
    echo "Usage: $0 <url> <expected_code> [timeout]" >&2
    exit 1
fi

# Execute curl
# -sL: Silent and follow redirects
# --max-time: Total time in seconds
# -o /dev/null: Ignore body
# -w: Write out only the status code
ACTUAL_CODE=$(curl -sL --max-time "$TIMEOUT" -o /dev/null -w "%{http_code}" "$URL")

# Logic Check
if [ "$ACTUAL_CODE" == "000" ]; then
    echo "error: Could not connect or request timed out" >&2
    exit 1
elif [ "$ACTUAL_CODE" -eq "$EXPECTED_CODE" ]; then
    echo "ok"
else
    echo "error: status $ACTUAL_CODE (expected $EXPECTED_CODE)" >&2
    exit 1
fi
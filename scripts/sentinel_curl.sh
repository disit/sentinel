#!/bin/bash

# Assign parameters to variables
# $1 is the URL
# ${2:-10} means use the second argument if provided, otherwise default to 10
URL=$1
TIMEOUT=${2:-10}

# Check if URL is provided
if [ -z "$URL" ]; then
    echo "Usage: $0 <url> [timeout]" >&2
    exit 1
fi

# Execute the curl command
# --max-time (or -m) sets the total time the operation is allowed to take
curl -ILsSf --max-time "$TIMEOUT" "$URL"
#!/bin/bash
cd /var/www/html/dashboardSmartCity/ScheduledTasks
# Arguments
COMMAND="$1"
LOG_PATH="$2"
MAX_HOURS="$3"
DELTA_HOURS="${4:-0}"  # optional, defaults to 0

# Sanitize LOG_PATH for marker filenames (replace / with _)
LOG_TAG=$(echo "$LOG_PATH" | sed 's|/|_|g')
SUCCESS_FILE="latest-success-$LOG_TAG"
FAILURE_FILE="latest-failure-$LOG_TAG"

# Run the command
eval "$COMMAND"
COMMAND_EXIT=$?

# Current datetime
NOW_DATETIME=$(date '+%Y-%m-%d %H:%M:%S')

if [[ $COMMAND_EXIT -ne 0 ]]; then
  echo "Error: Command '$COMMAND' failed with exit code $COMMAND_EXIT." >&2
  echo "$NOW_DATETIME" >> "$FAILURE_FILE"
else
  echo "Command '$COMMAND' was executed and it ended without failures."
  echo "$NOW_DATETIME" >> "$SUCCESS_FILE"
fi

# Check success/failure history
if [[ -f "$SUCCESS_FILE" ]]; then
  LAST_SUCC=$(tail -n 1 "$SUCCESS_FILE")
  SUCC_EPOCH=$(date -d "$LAST_SUCC" +%s)
else
  echo "Error: No successful run recorded yet." >&2
  SUCC_EPOCH=0
fi

if [[ -f "$FAILURE_FILE" ]]; then
  LAST_FAIL=$(tail -n 1 "$FAILURE_FILE")
  FAIL_EPOCH=$(date -d "$LAST_FAIL" +%s)
else
  FAIL_EPOCH=0
fi

# Warn if latest failure is more recent than latest success
if (( SUCC_EPOCH > 0 && FAIL_EPOCH > SUCC_EPOCH )); then
  echo "Warning: Latest failure ($LAST_FAIL) is more recent than latest success ($LAST_SUCC)." >&2
fi


# Check if log file exists
# This shouldn't happen, as the command ran should create it
if [[ ! -f "$LOG_PATH" ]]; then
  echo "Error: Log file '$LOG_PATH' not found." >&2
  exit 1
fi

# Get the last line of the log
LAST_LINE=$(tail -n 1 "$LOG_PATH")

# Extract the timestamp (last 19 characters should match YYYY-MM-DD HH:MM:SS)
LOG_DATETIME=$(echo "$LAST_LINE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$')

if [[ -z "$LOG_DATETIME" ]]; then
  echo "Error: Could not extract datetime from last log line." >&2
  exit 2
fi

# Convert datetime to epoch
LOG_EPOCH=$(date -d "$LOG_DATETIME" +%s 2>/dev/null)
NOW_EPOCH=$(date +%s)

if [[ -z "$LOG_EPOCH" ]]; then
  echo "Error: Failed to parse datetime '$LOG_DATETIME'." >&2
  exit 3
fi

# Compute difference in hours
DIFF_SECONDS=$((NOW_EPOCH - LOG_EPOCH))
DIFF_HOURS=$((DIFF_SECONDS / 3600))

# Apply delta
ADJUSTED_DIFF=$((DIFF_HOURS + DELTA_HOURS))

# Compare
if (( ADJUSTED_DIFF <= MAX_HOURS )); then
  echo "Log is fresh: last entry is $ADJUSTED_DIFF hour(s) old (unadjusted: $DIFF_HOURS, limit: $MAX_HOURS)."
  exit 0
else
  echo "Log is too old: last entry is $ADJUSTED_DIFF hour(s) old (unadjusted: $DIFF_HOURS, limit: $MAX_HOURS)." >&2
  exit 4
fi

# use this to run

#  docker exec -i dashboard-cron /bin/bash -s < some_commands.sh



# first
FILE_FIRST="/var/www/html/dashboardSmartCity/ScheduledTasks/running2-os.txt"

if [ ! -e "$FILE_FIRST" ]; then
    # not stuck
    echo "run-micro-os.sh is not currently running"
else
    # if process is running, it is not stuck
    output_first=$(pgrep -af run-micro-os.sh)
    if [ -n "$output_first" ]; then
        echo "run-micro-os.sh is currently running"
    else
        echo "run-micro-os.sh is not currently running, but because running2-os.txt exists, it is stuck! Will remove the file now" >&2
        rm /var/www/html/dashboardSmartCity/ScheduledTasks/running2-os.txt
    fi
fi
#print logs here...

# 1/6 done

last_log_IOT_Device_FeedAndUpdate_DashboardWizard_OS=""
while IFS= read -r line; do
    if [[ $line =~ Ingestion\ progress:\ [0-9]+% ]]; then
        last_log_IOT_Device_FeedAndUpdate_DashboardWizard_OS="${BASH_REMATCH[0]}"
    fi
done < /var/www/html/dashboardSmartCity/ScheduledTasks/feed-iot-os.log

if [ -n "$last_log_IOT_Device_FeedAndUpdate_DashboardWizard_OS" ]; then
    echo "Latest % progess of feed-iot-os.log:"
    echo "$last_log_IOT_Device_FeedAndUpdate_DashboardWizard_OS"
else
    echo "No % found, printing last 3 lines of feed-iot-os.log..."
    tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-iot-os.log
fi

echo ""

# 1/6 there's no progress log in php
# script done

echo "Printing last 3 lines of feed-iot-os.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-iot-os.log
echo ""

# 2/6 issue in run-micro-os.sh won't allow for printing anyway (wrong php called in run-micro-os.sh), there's no progress log in php
# script done

echo "Printing last 3 lines of feed-iot-app-os.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-iot-app-os.log
echo ""

# 3/6 there's no progress log in php, done

echo "Printing last 3 lines of feed-personaldata-os.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-personaldata-os.log
echo ""

# 4/6 there's no progress log in php, done

echo "Printing last 3 lines of synoptic-update-os.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/synoptic-update-os.log
echo ""

# 5/6 there's no progress log in php, done

echo "Printing last 3 lines of feed-heatmap-os.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-heatmap-os.log
echo ""

# 6/6 there's no progress log in php, done

echo "Printing last 3 lines of mykpicheck-os.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/mykpicheck-os.log
echo ""


# second
FILE_SECOND="/var/www/html/dashboardSmartCity/ScheduledTasks/running-health-os.txt"

if [ ! -e "$FILE_SECOND" ]; then
    # not stuck
    echo "run-health-os.sh is not currently running"
else
    echo "running-health-os.txt exists, run-health-os.sh may be currently running"
    output_second=$(pgrep -af run-health-os.sh)

    if [ -n "$output_second" ]; then
        echo "run-health-os.sh is currently running"
    else
        echo "run-health-os.sh is not currently running, but because running-health-os.txt exists, it is stuck! Will remove the file now" >&2
        rm /var/www/html/dashboardSmartCity/ScheduledTasks/running-health-os.txt
    fi
fi

# printing logs here...

# 1/1 there's no progress log in php, done

echo "Printing last 3 lines of health-os.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/health-os.log
echo ""

# third
FILE_THIRD="/var/www/html/dashboardSmartCity/ScheduledTasks/running2.txt"

if [ ! -e "$FILE_THIRD" ]; then
    # not stuck
    echo "run-iotapp.sh is not currently running"
else
    output_first=$(pgrep -af run-iotapp.sh)

    if [ -n "$output_first" ]; then
        echo "run-iotapp.sh is currently running"
    else
        echo "run-iotapp.sh is not currently running, but because running2.txt exists, it is stuck! Will remove the file now" >&2
        rm /var/www/html/dashboardSmartCity/ScheduledTasks/running2.txt
    fi
fi
# printing logs here...

# 1/6 there's no progress log in php, done

echo "Printing last 3 lines of feed-iot-2021.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-iot-2021.log
echo ""

# 2/6 there's no progress log in php, done

echo "Printing last 3 lines of feed-iot-app.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-iot-app.log
echo ""

# 3/6 there's no progress log in php, done

echo "Printing last 3 lines of feed-personaldata.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-personaldata.log
echo ""

# 4/6 there's no progress log in php, done

echo "Printing last 3 lines of feed-iot-act.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/feed-iot-act.log
echo ""

# 5/6 there's no progress log in php, done

echo "Printing last 3 lines of synoptic-update.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/synoptic-update.log
echo ""

# 6/6 Heatmap_FeedDashboardWizard.php isn't printed to anything, will pretend it goes to new-log.log, done

echo "Printing last 3 lines of heatmap.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/heatmap.log



# fourth
FILE_FOURTH="/var/www/html/dashboardSmartCity/ScheduledTasks/running-health.txt"

if [ ! -e "$FILE_FOURTH" ]; then
    # not stuck
    echo "run-health.sh is not currently running"
else
    output_first=$(pgrep -af run-health.sh)

    if [ -n "$output_first" ]; then
        echo "run-health.sh is currently running"
    else
        echo "run-health.sh is not currently running, but because running-health.txt exists, it is stuck! Will remove the file now" >&2
        rm /var/www/html/dashboardSmartCity/ScheduledTasks/running-health.txt
    fi
fi

# print logs here...

# 1/1 there's no progress log in php, done

echo "Printing last 3 lines of health.log..."
tail -n 3 /var/www/html/dashboardSmartCity/ScheduledTasks/health.log
echo ""
#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
#php HealthinessCheck.php > health.log 2>&1
output_first=$(pgrep -af HealthinessCheck.php)
if [ -n "$output_first" ]; then
    echo "HealthinessCheck.php is running" >> running-health.txt
    date >> running-iotapp-os.txt
else
    echo "HealthinessCheck.php is not running, starting..." >> running-health.txt
    date >> running-iotapp-os.txt
    php HealthinessCheck.php > health.log 2>&1 &
fi

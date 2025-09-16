#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
#php -d memory_limit=2G HealthinessCheck-OS.php > health-os.log 2>&1
output_first=$(pgrep -af HealthinessCheck-OS.php)
if [ -n "$output_first" ]; then
    echo "HealthinessCheck-OS.php is running" >> running-health-os.txt
    date >> running-health-os.txt
else
    echo "HealthinessCheck-OS.php is not running, starting..." >> running-health-os.txt
    date >> running-health-os.txt
    php HealthinessCheck-OS.php > health-os.log 2>&1 &
fi


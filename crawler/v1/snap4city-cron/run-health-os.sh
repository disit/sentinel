#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks

#php -d memory_limit=2G HealthinessCheck-OS.php > health-os.log 2>&1
output_first=$(pgrep -af HealthinessCheck_CarPark_Predictions.php)
if [ -n "$output_first" ]; then
    echo "HealthinessCheck_CarPark_Predictions.php is running" >> running-10min.txt
    date >> running-10min.txt
else
    echo "HealthinessCheck_CarPark_Predictions.php is not running, starting..." >> running-10min.txt
    date >> running-10min.txt
    php -d memory_limit=2G HealthinessCheck_CarPark_Predictions.php > health-carpark-pred.log 2>&1 &
fi

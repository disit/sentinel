#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
#php -d memory_limit=3G IOT_Last10min_Feed_DashboardWizard.php > feed-iot-last10m.log 2>&1
output_first=$(pgrep -af IOT_Last10min_Feed_DashboardWizard.php)
if [ -n "$output_first" ]; then
    echo "IOT_Last10min_Feed_DashboardWizard.php is running" >> running-last-10m-iot.txt
    date >> running-last-10m-iot.txt
else
    echo "IOT_Last10min_Feed_DashboardWizard.php is not running, starting..." >> running-last-10m-iot.txt
    date >> running-last-10m-iot.txt
    php -d memory_limit=3G IOT_Last10min_Feed_DashboardWizard.php > feed-iot-last10m.log 2>&1 &
fi

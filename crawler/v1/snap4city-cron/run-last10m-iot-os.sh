#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
#php -d memory_limit=2G IOT_Last10min_Feed_DashboardWizard-OS.php > feed-iot-last10m-os.log 2>&1
output_first=$(pgrep -af IOT_Last10min_Feed_DashboardWizard-OS.php)
if [ -n "$output_first" ]; then
    echo "IOT_Last10min_Feed_DashboardWizard-OS.php is running" >> running-last-10m-iot-os.txt
    date >> running-last-10m-iot-os.txt
else
    echo "IOT_Last10min_Feed_DashboardWizard-OS.php is not running, starting..." >> running-last-10m-iot-os.txt
    date >> running-last-10m-iot-os.txt
    php -d memory_limit=2G IOT_Last10min_Feed_DashboardWizard-OS.php > feed-iot-last10m-os.log 2>&1 &
fi

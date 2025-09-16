#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
#php -d memory_limit=5G IOT_Device_FeedAndUpdate_DashboardWizard-OS.php > feed-iot-os.log 2>&1
output_first=$(pgrep -af IOT_Device_FeedAndUpdate_DashboardWizard-OS.php)
if [ -n "$output_first" ]; then
    echo "Synoptic_Update_DashboardWizard-OS.php is running" >> running2-os.txt
    date >> running2-os.txt
else
    echo "Synoptic_Update_DashboardWizard-OS.php is not running, starting..." >> running2-os.txt
    date >> running2-os.txt
    php -d memory_limit=5G IOT_Device_FeedAndUpdate_DashboardWizard-OS.php > feed-iot-os.log 2>&1 &
fi


#php -d memory_limit=2G Synoptic_Update_DashboardWizard-OS.php > health-os.log 2>&1
output_second=$(pgrep -af Synoptic_Update_DashboardWizard-OS.php)
if [ -n "$output_second" ]; then
    echo "Synoptic_Update_DashboardWizard-OS.php is running" >> running2-os.txt
    date >> running2-os.txt
else
    echo "Synoptic_Update_DashboardWizard-OS.php is not running, starting..." >> running2-os.txt
    date >> running2-os.txt
    php -d memory_limit=2G Synoptic_Update_DashboardWizard-OS.php > health-os.log 2>&1 &
fi


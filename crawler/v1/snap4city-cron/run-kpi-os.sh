#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
#php -d memory_limit=2G Personal_Data_FeedDashboardWizard-OS.php > feed-personaldata-os.log 2>&1 
output_first=$(pgrep -af Personal_Data_FeedDashboardWizard-OS.php)
if [ -n "$output_first" ]; then
    echo "Synoptic_Update_DashboardWizard-OS.php is running" >> running3-os.txt
    date >> running3-os.txt
else
    echo "Synoptic_Update_DashboardWizard-OS.php is not running, starting..." >> running3-os.txt
    date >> running3-os.txt
    php -d memory_limit=2G Personal_Data_FeedDashboardWizard-OS.php > feed-personaldata-os.log 2>&1  &
fi

#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks

#php -d memory_limit=2G Heatmap_FeedDashboardWizard-OS.php > heatmap-os.log 2>&1
output_first=$(pgrep -af Heatmap_FeedDashboardWizard-OS.php)
if [ -n "$output_first" ]; then
    echo "Heatmap_FeedDashboardWizard-OS.php is running" >> running-os.txt
    date >> running-os.txt
else
    echo "Heatmap_FeedDashboardWizard-OS.php is not running, starting..." >> running-os.txt
    date >> running-os.txt
    php -d memory_limit=2G Heatmap_FeedDashboardWizard-OS.php > heatmap-os.log 2>&1 &
fi

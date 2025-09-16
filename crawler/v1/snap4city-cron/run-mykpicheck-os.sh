#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
#php -d memory_limit=2G MyKPICheck-OS.php > mykpicheck-os.log 2>&1
output_first=$(pgrep -af MyKPICheck-OS.php)
if [ -n "$output_first" ]; then
    echo "MyKPICheck-OS.php is running" >> running-mykpicheck-os.txt
    date >> running-mykpicheck-os.txt
else
    echo "MyKPICheck-OS.php is not running, starting..." >> running-mykpicheck-os.txt
    date >> running-mykpicheck-os.txt
    php -d memory_limit=2G MyKPICheck-OS.php > mykpicheck-os.log 2>&1 &
fi

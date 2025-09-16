#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
if [ -f running.txt ]; then
  echo still running
  exit
fi

date > running.txt
php FeedDasbhoardWizard.php > feed.log 2>&1
php FeedDashboardWizard205.php > feed205.log 2>&1 
#php IOT_Sensor_FeedDashboardWizard.php > feed-iot.log 2>&1 
#php FeedTwitterExternalContent.php > twitter.log 2>&1
php FeedDashboardWizard_Previ_meteo.php > meteo.log 2>&1
php Heatmap_FeedDashboardWizard.php > heatmap.log 2>&1
#php HealthinessCheck.php > health.log 2>&1
rm running.txt


#php FeedDasbhoardWizard.php > feed.log 2>&1
output_first=$(pgrep -af FeedDasbhoardWizard.php)
if [ -n "$output_first" ]; then
    echo "FeedDasbhoardWizard.php is running" >> running.txt
    date >> running.txt
else
    echo "FeedDasbhoardWizard.php is not running, starting..." >> running.txt
    date >> running.txt
    php -d php FeedDasbhoardWizard.php > feed.log 2>&1 &
fi

#php FeedDashboardWizard_Previ_meteo.php > meteo.log 2>&1
output_third=$(pgrep -af FeedDashboardWizard_Previ_meteo.php)
if [ -n "$output_third" ]; then
    echo "FeedDashboardWizard_Previ_meteo.php is running" >> running.txt
    date >> running.txt
else
    echo "FeedDashboardWizard_Previ_meteo.php is not running, starting..." >> running.txt
    date >> running.txt
    php -d php FeedDashboardWizard_Previ_meteo.php > meteo.log 2>&1 &
fi

#php Heatmap_FeedDashboardWizard.php > heatmap.log 2>&1
output_fourth=$(pgrep -af Heatmap_FeedDashboardWizard.php)
if [ -n "$output_fourth" ]; then
    echo "Heatmap_FeedDashboardWizard.php is running" >> running.txt
    date >> running.txt
else
    echo "Heatmap_FeedDashboardWizard.php is not running, starting..." >> running.txt
    date >> running.txt
    php -d php Heatmap_FeedDashboardWizard.php > heatmap.log 2>&1 &
fi

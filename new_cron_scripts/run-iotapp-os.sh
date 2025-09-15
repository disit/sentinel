#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks
#php -d memory_limit=2G IOT_Device_FeedAndUpdate_DashboardWizard-OS.php > feed-iot-os.log 2>&1
output_first=$(pgrep -af IOT_Sensor_Feed_DashboardWizard.php)
if [ -n "$output_first" ]; then
    echo "IOT_Sensor_Feed_DashboardWizard.php is running" >> running-iotapp-os.txt
    date >> running-iotapp-os.txt
else
    echo "IOT_Sensor_Feed_DashboardWizard.php is not running, starting..." >> running-iotapp-os.txt
    date >> running-iotapp-os.txt
    php -d memory_limit=2G IOT_Device_FeedAndUpdate_DashboardWizard-OS.php > feed-iot-os.log 2>&1 &
fi
#php IOT_Sensor_Feed_DashboardWizard.php > feed-iot-new.log 2>&1
#date >> running2.txt
#php IOT_App_FeedDashboardWizard.php > feed-iot-app.log 2>&1 
#date >> running2.txt
#php Personal_Data_FeedDashboardWizard.php > feed-personaldata.log 2>&1 
#php IOT_Actuator_FeedDashboardWizard.php > feed-iot-act.log 2>&1
#date >> running2.txt
#php IOT_Actuator_FeedDashboardWizard205.php > feed-iot-act205.log 2>&1


#php -d memory_limit=2G Synoptic_Update_DashboardWizard-OS.php > synoptic-update-os.log 2>&1
output_first=$(pgrep -af Synoptic_Update_DashboardWizard.php)
if [ -n "$output_first" ]; then
    echo "Synoptic_Update_DashboardWizard.php is running" >> running-iotapp-os.txt
    date >> running-iotapp-os.txt
else
    echo "Synoptic_Update_DashboardWizard.php is not running, starting..." >> running-iotapp-os.txt
    date >> running-iotapp-os.txt
    php -d memory_limit=2G Synoptic_Update_DashboardWizard-OS.php > synoptic-update-os.log 2>&1 &
fi
php -d memory_limit=2G Synoptic_Update_DashboardWizard-OS.php > synoptic-update-os.log 2>&1

#date >> running2.txt
#php BIM_FeedDashboardWizard.php > bim.log 2>&1

#!/bin/sh
cd /var/www/html/dashboardSmartCity/ScheduledTasks

#php IOT_Sensor_Feed_DashboardWizard.php >> feed-iot-new.log 2>&1
output_first=$(pgrep -af IOT_Sensor_Feed_DashboardWizard.php)
if [ -n "$output_first" ]; then
    echo "IOT_Sensor_Feed_DashboardWizard.php is running" >> running2.txt
    date >> running2.txt
else
    echo "IOT_Sensor_Feed_DashboardWizard.php is not running, starting..." >> running2.txt
    date >> running2.txt
    php IOT_Sensor_Feed_DashboardWizard.php > feed-iot-new.log 2>&1 &
fi
#php IOT_App_FeedDashboardWizard.php >> feed-iot-app.log 2>&1 
output_second=$(pgrep -af IOT_App_FeedDashboardWizard.php)
if [ -n "$output_second" ]; then
    echo "IOT_App_FeedDashboardWizard.php is running" >> running2.txt
    date >> running2.txt
else
    echo "IOT_App_FeedDashboardWizard.php is not running, starting..." >> running2.txt
    date >> running2.txt
    php IOT_App_FeedDashboardWizard.php > feed-iot-app.log 2>&1 &
fi

#php Personal_Data_FeedDashboardWizard.php >> feed-personaldata.log 2>&1 
output_third=$(pgrep -af Personal_Data_FeedDashboardWizard.php)
if [ -n "$output_third" ]; then
    echo "Personal_Data_FeedDashboardWizard.php is running" >> running2.txt
    date >> running2.txt
else
    echo "Personal_Data_FeedDashboardWizard.php is not running, starting..." >> running2.txt
    date >> running2.txt
    php Personal_Data_FeedDashboardWizard.php > feed-personaldata.log 2>&1 &
fi

#php IOT_Actuator_FeedDashboardWizard.php >> feed-iot-act.log 2>&1 
output_fourth=$(pgrep -af Personal_Data_FeedDashboardWizard.php)
if [ -n "$output_fourth" ]; then
    echo "IOT_Actuator_FeedDashboardWizard.php is running" >> running2.txt
    date >> running2.txt
else
    echo "IOT_Actuator_FeedDashboardWizard.php is not running, starting..." >> running2.txt
    date >> running2.txt
    php IOT_Actuator_FeedDashboardWizard.php > feed-iot-act.log 2>&1 &
fi

#php IOT_Actuator_FeedDashboardWizard205.php >> feed-iot-act205.log 2>&1 
output_fourth_2=$(pgrep -af IOT_Actuator_FeedDashboardWizard205.php)
if [ -n "$output_fourth_2" ]; then
    echo "IOT_Actuator_FeedDashboardWizard205.php is running" >> running2.txt
    date >> running2.txt
else
    echo "IOT_Actuator_FeedDashboardWizard205.php is not running, starting..." >> running2.txt
    date >> running2.txt
    php IOT_Actuator_FeedDashboardWizard205.php > feed-iot-act205.log 2>&1 &
fi

#php Synoptic_Update_DashboardWizard.php >> synoptic-update.log 2>&1
output_fifth=$(pgrep -af Synoptic_Update_DashboardWizard.php)
if [ -n "$output_fifth" ]; then
    echo "Synoptic_Update_DashboardWizard.php is running" >> running2.txt
    date >> running2.txt
else
    echo "Synoptic_Update_DashboardWizard.php is not running, starting..." >> running2.txt
    date >> running2.txt
    php Synoptic_Update_DashboardWizard.php > synoptic-update.log 2>&1 &
fi


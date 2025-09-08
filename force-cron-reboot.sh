docker exec -it dashboard-crontab bash -c 'rm /var/www/html/dashboardSmartCity/ScheduledTasks/running2-os.txt /var/www/html/dashboardSmartCity/ScheduledTasks/running-health-os.txt /var/www/html/dashboardSmartCity/ScheduledTasks/running2.txt /var/www/html/dashboardSmartCity/ScheduledTasks/running-health.txt'
docker restart dashboard-crontab

#### /var/www/html/dashboardSmartCity/ScheduledTasks/running-health-os.txt /var/www/html/dashboardSmartCity/ScheduledTasks/running-health.txt

kubectl exec deployment/dashboard-crontab -n sentinel-deployment -- bash -c 'rm /var/www/html/dashboardSmartCity/ScheduledTasks/running2-os.txt /var/www/html/dashboardSmartCity/ScheduledTasks/running-health-os.txt /var/www/html/dashboardSmartCity/ScheduledTasks/running2.txt /var/www/html/dashboardSmartCity/ScheduledTasks/running-health.txt'
kubectl rollout dashboard-crontab -n sentinel-deployment

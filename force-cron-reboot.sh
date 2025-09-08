docker exec -it dashboard-crontab bash -c 'rm /var/www/html/dashboardSmartCity/ScheduledTasks/running.txt'
docker restart dashboard-crontab

####

kubectl exec deployment/dashboard-crontab -n sentinel-deployment -- bash -c 'rm /var/www/html/dashboardSmartCity/ScheduledTasks/running.txt'
kubectl rollout dashboard-crontab -n sentinel-deployment

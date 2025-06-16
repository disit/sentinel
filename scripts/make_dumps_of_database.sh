#!/bin/bash

docker exec dashboarddb mysqldump -uroot -p'$#dashboard-db-pwd-admin#$' --all-databases > mysql_dump.sql # this copies logs which are gonna be huge
#echo "USE Dashboard;" > mysql_dump.sql
#docker exec dashboarddb mysqldump -uroot -p'$#dashboard-db-pwd-admin#$' Dashboard Widgets WidgetsIconsMap multilanguage HeatmapRanges HeatmapColorLevels MainMenu MainMenuSubmenus >> mysql_dump.sql
#echo "USE iotdb;" > mysql_dump.sql
#docker exec dashboarddb mysqldump -uroot -p'$#dashboard-db-pwd-admin#$' iotdb functionalities mainmenu defaultpolicy formats protocols data_types defaultcontestbrokerpolicy >> mysql_dump.sql
#todo what if multiple mongos?
docker exec $#virtuoso-kb-pwd#$ mkdir -p /usr/local/virtuoso-opensource/share/virtuoso/vad/dump.nq; docker exec virtuoso-kb isql-v localhost dba $#virtuoso-kb-pwd#$ exec="dump_nquads('/usr/local/virtuoso-opensource/share/virtuoso/vad/dump.nq')"; docker cp virtuoso-kb:/usr/local/virtuoso-opensource/share/virtuoso/vad/dump.nq virtuoso_dump.nq; docker exec virtuoso-kb rm -rf /usr/local/virtuoso-opensource/share/virtuoso/vad/dump.nq
docker exec od-postgis pg_dumpall -U postgres > postgres_od-postgis_dump.sql
docker exec postgres-db pg_dumpall -U keycloak > postgres_postgres-db_dump.sql


echo date > sysinfo.txt
date >> sysinfo.txt
echo cpu info >> sysinfo.txt
lscpu >> sysinfo.txt
echo hd info >> sysinfo.txt
lsblk >> sysinfo.txt
echo bus tree info >> sysinfo.txt
lspci >> sysinfo.txt
#todo postgres-s geoserver is cursed and doesn't like any user or password

rm -r php-css-dump
docker exec dashboard-builder sh -c 'cd /var/www/html && tar czf - $(find . "*.php" -o -name "*.css")'
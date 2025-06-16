#!/bin/bash
containers=$(docker ps -a --format "table {{.Names}}")
iotapp="iotapp"
count=$(awk -v target="$iotapp" 'BEGIN {IGNORECASE=0} {count+=gsub(target, "")} END{print count}' <<< "$containers")
for ((i=1; i<=count; i++)); do
    formatted_number=$(printf "%03d" "$i")
	port_number=$(($i+1879))
	url="http://localhost:$port_number/iotapp/iotapp-$formatted_number/"
	result=$(curl -LI $url -o /dev/null -w '%{http_code}\n' -s)
	echo $url answered $result, and it should be 200 \<br\>\<\\br\>
done

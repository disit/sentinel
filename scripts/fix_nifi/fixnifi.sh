#!/bin/bash
token=$(curl --insecure --header 'Content-Type: application/x-www-form-urlencoded' --data-urlencode 'username=admin' --data-urlencode 'password=$#nifi-password#$' -X POST "https://localhost:9090/nifi-api/access/token" -s)

echo "token for authentication: $token"

connection_id=$(curl --location 'https://localhost:9090/nifi-api/process-groups/002651c8-016f-1000-f2fa-50ea0c27c262/connections' --header 'Accept: application/json, text/javascript, */*; q=0.01' --header 'Content-Type: application/json' --header "Authorization: Bearer $token" --insecure --data '{"revision":{"clientId":"d9bdef0e-0190-1000-05f5-285680433415","version":0},"disconnectedNodeAcknowledged":false,"component":{"name":"","source":{"id":"1ab166f0-0181-1000-73e7-9e9cd497f516","groupId":"002651c8-016f-1000-f2fa-50ea0c27c262","type":"FUNNEL"},"destination":{"id":"1aaf23b4-0181-1000-6fa8-a851c53e2ebd","groupId":"002651c8-016f-1000-f2fa-50ea0c27c262","type":"PROCESSOR"},"flowFileExpiration":"0 sec","backPressureDataSizeThreshold":"1 GB","backPressureObjectThreshold":"10000","bends":[],"prioritizers":[],"loadBalanceStrategy":"DO_NOT_LOAD_BALANCE","loadBalancePartitionAttribute":"","loadBalanceCompression":"DO_NOT_COMPRESS"}}' -s|jq -r '.id')

echo "created the connection $connection_id"

echo

echo waiting 10 seconds...

sleep 10

revision_enrich=$(curl 'https://localhost:9090/nifi-api/processors/03fcba02-017c-1000-10b5-1b63ebcd9871' -H "Authorization: Bearer $token" --compressed --insecure -s| jq -r '.revision.version') 

echo get revision_enrich: $revision_enrich

curl -k -X PUT 'https://localhost:9090/nifi-api/processors/03fcba02-017c-1000-10b5-1b63ebcd9871' -H "Authorization: Bearer $token" --compressed --insecure -H 'Content-Type: application/json' -d "{ \"revision\": { \"version\": $revision_enrich }, \"component\": { \"id\": \"03fcba02-017c-1000-10b5-1b63ebcd9871\", \"state\": \"STOPPED\" }}" -s

echo stop enrich

revision_script=$(curl 'https://localhost:9090/nifi-api/processors/1aaf23b4-0181-1000-6fa8-a851c53e2ebd' -H "Authorization: Bearer $token" --compressed --insecure -s| jq -r '.revision.version')

echo
echo get revision_script: $revision_script
revision_script=$((revision_script))
curl -k -X PUT 'https://localhost:9090/nifi-api/processors/1aaf23b4-0181-1000-6fa8-a851c53e2ebd' -H "Authorization: Bearer $token" --compressed --insecure -H 'Content-Type: application/json' -d "{ \"revision\": { \"version\": $revision_script }, \"component\": { \"id\": \"1aaf23b4-0181-1000-6fa8-a851c53e2ebd\", \"state\": \"STOPPED\" }}" -s

sleep 3
echo
echo stop script

curl --location --request DELETE "https://localhost:9090/nifi-api/connections/$connection_id?version=1&clientId=$connection_id&disconnectedNodeAcknowledged=false" --insecure --header 'Accept: application/json, text/javascript, */*; q=0.01' -H "Authorization: Bearer $token" -s
echo
echo deleted the connection
sleep 3
revision_enrich=$((revision_enrich + 1))
curl -k -X PUT 'https://localhost:9090/nifi-api/processors/03fcba02-017c-1000-10b5-1b63ebcd9871' -H "Authorization: Bearer $token" --compressed --insecure -H 'Content-Type: application/json' -d "{ \"revision\": { \"version\": $revision_enrich }, \"component\": { \"id\": \"03fcba02-017c-1000-10b5-1b63ebcd9871\", \"state\": \"RUNNING\" }}" -s
echo
echo resume enrich
sleep 3
revision_script=$((revision_script + 1))
curl -k -X PUT 'https://localhost:9090/nifi-api/processors/1aaf23b4-0181-1000-6fa8-a851c53e2ebd' -H "Authorization: Bearer $token" --compressed --insecure -H 'Content-Type: application/json' -d "{ \"revision\": { \"version\": $revision_script }, \"component\": { \"id\": \"1aaf23b4-0181-1000-6fa8-a851c53e2ebd\", \"state\": \"RUNNING\" }}" -s
echo
echo resume script


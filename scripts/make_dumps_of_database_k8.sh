#!/bin/bash
# Configuration
DB_HOST="dashboarddb"
DB_USER="root"
db-passwd="$#dashboard-db-pwd-admin#$"
DUMP_FILE="backup.sql"


# Run the dump
echo "Dumping database..."
mysqldump -h $DB_HOST -u $DB_USER -p$db-passwd --all-databases > "backup.sql"

if [ $? -eq 0 ]; then
    echo "Database dumped successfully to $DUMP_FILE"
else
    echo "mysqldump failed."
    exit 1
fi

endpoint="http://virtuoso-kb:8890/sparql"

# Get list of named graphs
graphs=$(curl -s -G \
  --data-urlencode "query=SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }" \
  -H "Accept: application/sparql-results+json" \
  "$endpoint" | jq -r '.results.bindings[].g.value')

# Loop through graphs and export
for graph in $graphs; do
  echo "Dumping $graph..."
  encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$graph'''))")
  curl -s -G \
    --data-urlencode "query=CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <$graph> { ?s ?p ?o } }" \
    -H "Accept: application/rdf+xml" \
    "$endpoint" \
    -o "dump_$(basename $encoded).rdf"
done


# Configuration
PG_HOST="od-postgis"
PG_PORT="5432"
PG_USER="postgres"
PG_PASS="$#postgre-password#$"
DUMP_FILE="remote_postgres_backup_od.sql"


# Check for pg_dumpall
if ! command -v pg_dumpall &> /dev/null; then
    echo "pg_dumpall not found. Installing..."
    apt-get update
    apt-get install -y postgresql-client
fi

# Dump all databases remotely
echo "Dumping all PostgreSQL databases from $PG_HOST..."
pg_dumpall -h $PG_HOST -p $PG_PORT -U $PG_USER > "$DUMP_FILE"

# Check result
if [ $? -eq 0 ]; then
    echo "Remote databases dumped successfully to $DUMP_FILE"
else
    echo "pg_dumpall failed."
    exit 1
fi

PG_HOST_K="postgres-db"
PG_PORT_K="5432"
PG_USER_K="keycloak"
PG_PASS="$#dashboard-db-pwd#$"
DUMP_FILE_K="remote_postgres_backup_keycloak.sql"


# Dump all databases remotely
echo "Dumping all PostgreSQL databases from $PG_HOST_K..."
pg_dumpall -h "$PG_HOST_K" -p "$PG_PORT_K" -U "$PG_USER_K" > "$DUMP_FILE_K"

# Check result
if [ $? -eq 0 ]; then
    echo "Remote databases dumped successfully to $DUMP_FILE_K"
else
    echo "pg_dumpall failed."
    exit 1
fi

#todo postgres-s geoserver is cursed and doesn't like any user or password

POD=$(kubectl get pods -l app=dashboard-db -o jsonpath="{.items[0].metadata.name}")

kubectl exec -i $POD -- \
  sh -c 'cd /var/www/html && tar czf - $(find . \( -name "*.php" -o -name "*.css" \))' > files.tar.gz

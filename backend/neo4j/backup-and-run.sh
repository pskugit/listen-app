#!/bin/bash
neo4j start

# Load backup if it exists
if [ -f /backups/database.cypher ]; then
    echo "Loading exisiting Cypher export..."
    cypher-shell -u neo4j -p password -d neo4j -f /backups/database.cypher
elif [ -f /backups/database-initial.cypher ]; then
    echo "Loading Cypher export containing the inital database setup..."
    cypher-shell -u neo4j -p password -d neo4j -f /backups/database.cypher
fi

while true; do

    echo "Neo4j is running. Waiting for the next backup cycle..."

    # Wait for 5 minutes (300 seconds)
    sleep 60

    echo "Creating Cypher export..."

    # Perform the Cypher export while Neo4j is running
    cypher-shell -u neo4j -p password -d neo4j "CALL apoc.export.cypher.all('/backups/database.cypher', {useOptimizations: {type: 'UNWIND_BATCH', unwindBatchSize: 20}, format: 'plain'})"
    
    echo "Cypher export completed and saved to /backups/database.cypher"

done

# Use the official Neo4j community image as a base
FROM neo4j:latest

# Install curl
RUN apt-get update && apt-get install -y curl

# Create the plugins directory
RUN mkdir -p /plugins

# Download APOC plugin
RUN curl -o /plugins/apoc.jar https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/5.6.0/apoc-5.6.0-core.jar

# Create the /backups directory
RUN mkdir -p /backups && chmod 777 /backups

# Copy your backup-and-run.sh script to the container
COPY backup-and-run.sh /backup-and-run.sh

# Make sure the script is executable
RUN chmod +x /backup-and-run.sh

# Set the environment variable to point to your custom script
ENV EXTENSION_SCRIPT=/backup-and-run.sh

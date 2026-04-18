#!/bin/sh
mkdir -p /app/data
[ -f /app/data/state.json ] || echo '{}' > /app/data/state.json
[ -f /app/data/snapshot.json ] || echo '{}' > /app/data/snapshot.json
exec poetry run home-server

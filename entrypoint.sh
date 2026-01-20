#!/bin/sh
[ -f state.json ] || echo '{}' > state.json
[ -f snapshot.json ] || echo '{}' > snapshot.json
exec poetry run home-cli server

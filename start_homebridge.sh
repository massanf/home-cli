#!/bin/bash

# Ensure we are in the homebridge directory or can find it
if [ -d "homebridge" ]; then
    cd homebridge
fi

if [ ! -f "package.json" ]; then
    echo "Error: package.json not found. Are you in the right directory?"
    exit 1
fi

# Check if node_modules exists, if not install
if [ ! -d "node_modules" ]; then
    echo "Installing Homebridge dependencies..."
    npm install --cache .npm-cache
fi

echo "Starting Homebridge..."
npm start

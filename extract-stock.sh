#!/bin/bash

echo "Starting simple MCP server..."

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Build TypeScript if needed
if [ ! -d "build" ]; then
    echo "Building TypeScript..."
    npm run build
fi

# Run the server
node build/index.js

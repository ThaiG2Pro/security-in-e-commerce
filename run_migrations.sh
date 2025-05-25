#!/bin/bash

# This script runs Alembic migrations to update the database schema
# It's useful for testing migrations locally before deploying

set -e  # Exit immediately if a command exits with a non-zero status

# Install python-dotenv if not already installed
pip install python-dotenv || echo "Warning: Failed to install python-dotenv, continuing anyway..."

# Make sure the DATABASE_URL environment variable is set
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL environment variable is not set"
    echo "Using local SQLite database for testing"
    export DATABASE_URL="sqlite:///database.db"
fi

# Run the migrations
echo "Running database migrations..."
alembic upgrade head

echo "Database migration complete!"

#!/bin/bash

# This script runs Alembic migrations to update the database schema
# It's useful for testing migrations locally before deploying

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

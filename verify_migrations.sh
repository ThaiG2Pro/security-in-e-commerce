#!/bin/bash
# verify_migrations.sh - A script to verify Alembic migrations before deployment

echo "Checking Alembic migration files..."

# Check if alembic directory exists
if [ ! -d "alembic" ]; then
    echo "ERROR: alembic directory not found!"
    exit 1
fi

# Check if alembic.ini exists
if [ ! -f "alembic.ini" ]; then
    echo "ERROR: alembic.ini not found!"
    exit 1
fi

# Check for empty migration files
EMPTY_FILES=$(find alembic/versions -type f -name "*.py" -size 0)
if [ ! -z "$EMPTY_FILES" ]; then
    echo "ERROR: Found empty migration files:"
    echo "$EMPTY_FILES"
    echo "Please delete or properly populate these files."
    exit 1
fi

# Check for missing revision IDs in migration files
for file in alembic/versions/*.py; do
    if ! grep -q "revision = " "$file" && ! grep -q "revision: str = " "$file"; then
        echo "ERROR: Missing revision ID in $file"
        echo "Please add proper revision identifiers to this file."
        exit 1
    fi
done

# Check migration history
echo "Checking migration history..."
alembic history

echo "All migration files look good!"
exit 0

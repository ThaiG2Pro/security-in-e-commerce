#!/bin/bash
# check_dependencies.sh - Ensures all required dependencies are installed

set -e  # Exit immediately if a command exits with a non-zero status

echo "Checking and installing required dependencies..."

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Additional verification for critical dependencies
echo "Verifying critical dependencies..."

# List of critical packages that must be installed
CRITICAL_PACKAGES=("Flask" "gunicorn" "psycopg2-binary" "alembic" "python-dotenv")

for package in "${CRITICAL_PACKAGES[@]}"; do
    python -c "import importlib.util; print('✓ $package' if importlib.util.find_spec('${package}'.lower().replace('-', '_')) else '✗ $package is missing')" || {
        echo "Installing $package..."
        pip install "$package"
    }
done

echo "All dependencies verified and installed."
exit 0

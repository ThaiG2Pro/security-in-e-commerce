#!/usr/bin/env python
# test_db_connection.py - Script to test database connection

import os
from dotenv import load_dotenv
from models import get_db_connection

# Load environment variables
load_dotenv()

def test_connection():
    """Test the database connection using credentials from .env file."""
    try:
        print("Attempting to connect to database...")
        print(f"Database URL: {os.getenv('DATABASE_URL')}")
        
        # Try to establish connection
        conn = get_db_connection()
        
        # Get cursor
        cursor = conn.cursor()
        
        # Execute a simple query
        cursor.execute("SELECT current_database(), current_user, version();")
        db_name, db_user, version = cursor.fetchone()
        
        print("\nConnection successful!")
        print(f"Database: {db_name}")
        print(f"User: {db_user}")
        print(f"PostgreSQL version: {version.split(',')[0]}")
        
        # Close cursor and connection
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"\nError connecting to database: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()

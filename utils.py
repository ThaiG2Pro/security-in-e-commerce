# utils.py
from flask import session, redirect, url_for, after_this_request
import os
import psycopg2
import sys
from functools import wraps
# Use config instead of direct dotenv loading
import config

def get_db_connection():
    """Get a database connection with error handling.
    
    Returns:
        Connection: A database connection object
    """
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        return conn
    except psycopg2.OperationalError as e:
        print(f"Database connection error: {e}", file=sys.stderr)
        # For development, provide a fallback to SQLite
        if config.ENV == 'development':
            import sqlite3
            print("Falling back to SQLite for development", file=sys.stderr)
            return sqlite3.connect('database.db')
        else:
            # In production, re-raise the error
            raise

def add_security_headers():
    if os.getenv('SECURITY_HEADERS', 'false').lower() == 'true':
        @after_this_request
        def set_headers(response):
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
            return response

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session.get('role') != 'admin':
            return redirect(url_for('unauthorized'))
        return f(*args, **kwargs)
    return decorated_function

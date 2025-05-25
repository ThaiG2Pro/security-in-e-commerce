"""Configuration settings for the application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment
ENV = os.getenv('FLASK_ENV', 'development')

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')

# Secret key for session
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')

# Website URL for email links
if ENV == 'production':
    WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://your-app-name.onrender.com')
else:
    WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:5000')

# Cookie settings
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# Token expiry in hours
RESET_TOKEN_EXPIRY_HOURS = 24

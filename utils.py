# utils.py
from flask import session, redirect, url_for, after_this_request
import os
from functools import wraps

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

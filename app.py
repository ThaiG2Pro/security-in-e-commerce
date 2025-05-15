from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from models import is_db_empty, init_db, populate_sample_data
from admin_routes import admin_bp
from user_routes import user_bp

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

if os.getenv('FLASK_ENV', 'development') == 'development' or is_db_empty():
    init_db()
    populate_sample_data()

# Cấu hình session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

@app.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html')

app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)

if __name__ == '__main__':
    app.run(debug=True)
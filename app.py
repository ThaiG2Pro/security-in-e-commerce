import os
import psycopg2
import hashlib
import secrets
import json
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, make_response
from functools import wraps
from urllib.parse import urlencode

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.config['SESSION_COOKIE_NAME'] = '__Host-session'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_PATH'] = '/'

# Middleware to add Partitioned attribute to Set-Cookie
@app.after_request
def add_partitioned_cookie(response):
    if 'Set-Cookie' in response.headers:
        cookie_value = response.headers['Set-Cookie']
        if '; Partitioned' not in cookie_value:
            response.headers['Set-Cookie'] = cookie_value + '; Partitioned'
    return response

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Security headers configuration
SECURITY_HEADERS = os.getenv('SECURITY_HEADERS', 'true').lower() == 'true'

def apply_security_headers(response):
    if SECURITY_HEADERS:
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
    return response

# Inject script configuration
INJECT_SCRIPT = os.getenv('INJECT_SCRIPT', 'false').lower() == 'true'
SCRIPT_CONTENT = os.getenv('SCRIPT_CONTENT', '')

# Dummy products
products = [
    {"id": 1, "name": "Laptop", "price": 999.99, "image": "laptop.jpg"},
    {"id": 2, "name": "Smartphone", "price": 499.99, "image": "smartphone.jpg"},
    {"id": 3, "name": "Headphones", "price": 99.99, "image": "headphones.jpg"}
]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    cursor.execute("SELECT id, name, price, image FROM products")
    products = cursor.fetchall()
    response = make_response(render_template('index.html', products=products, inject_script=INJECT_SCRIPT, script_content=SCRIPT_CONTENT))
    return apply_security_headers(response)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        token = secrets.token_urlsafe(32)
        
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already registered"}), 400
        
        cursor.execute(
            "INSERT INTO users (email, password, verification_token, balance) VALUES (%s, %s, %s, %s) RETURNING id",
            (email, hashed_password, token, 1000.00)
        )
        user_id = cursor.fetchone()[0]
        conn.commit()
        
        verification_url = f"{request.url_root}verify?{urlencode({'email': email, 'token': token})}"
        print(f"Verification URL for {email}: {verification_url}")  # Log for demo
        
        response = make_response(jsonify({"message": "Registration successful. Please verify your email."}))
        return apply_security_headers(response)
    
    response = make_response(render_template('register.html', inject_script=INJECT_SCRIPT, script_content=SCRIPT_CONTENT))
    return apply_security_headers(response)

@app.route('/verify')
def verify():
    email = request.args.get('email')
    token = request.args.get('token')
    
    cursor.execute("SELECT id, verification_token FROM users WHERE email = %s", (email,))
    result = cursor.fetchone()
    if result and result[1] == token:
        cursor.execute("UPDATE users SET is_verified = TRUE, verification_token = NULL WHERE id = %s", (result[0],))
        conn.commit()
        response = make_response(jsonify({"message": "Email verified successfully"}))
    else:
        response = make_response(jsonify({"message": "Invalid verification link"}), 400)
    
    return apply_security_headers(response)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute("SELECT id, password, is_verified FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user and user[1] == hashed_password and user[2]:
            session['user_id'] = user[0]
            next_url = request.form.get('next') or url_for('index')
            response = make_response(redirect(next_url))
            return apply_security_headers(response)
        else:
            response = make_response(jsonify({"message": "Invalid credentials or unverified email"}), 401)
            return apply_security_headers(response)
    
    response = make_response(render_template('login.html', inject_script=INJECT_SCRIPT, script_content=SCRIPT_CONTENT))
    return apply_security_headers(response)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    response = make_response(redirect(url_for('index')))
    return apply_security_headers(response)

@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if not cursor.fetchone():
            response = make_response(jsonify({"message": "Invalid product ID"}), 400)
            return apply_security_headers(response)
        
        cursor.execute(
            "INSERT INTO cart (user_id, product_id) VALUES (%s, %s)",
            (session['user_id'], product_id)
        )
        conn.commit()
        response = make_response(jsonify({"message": "Product added to cart"}))
        return apply_security_headers(response)
    
    cursor.execute(
        "SELECT p.id, p.name, p.price, p.image FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = %s",
        (session['user_id'],)
    )
    cart_items = cursor.fetchall()
    total = sum(item[2] for item in cart_items)
    response = make_response(render_template('cart.html', cart_items=cart_items, total=total, inject_script=INJECT_SCRIPT, script_content=SCRIPT_CONTENT))
    return apply_security_headers(response)

@app.route('/delivery', methods=['GET', 'POST'])
@login_required
def delivery():
    prefilled_address = request.args.get('address', '')
    if request.method == 'POST':
        address = request.form['address']
        cursor.execute("UPDATE users SET delivery_address = %s WHERE id = %s", (address, session['user_id']))
        conn.commit()
        response = make_response(redirect(url_for('checkout')))
        return apply_security_headers(response)
    
    response = make_response(render_template('delivery.html', prefilled_address=prefilled_address, inject_script=INJECT_SCRIPT, script_content=SCRIPT_CONTENT))
    return apply_security_headers(response)

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cursor.execute(
        "SELECT p.id, p.name, p.price, p.image FROM cart c JOIN products p ON c.product_id = p.id WHERE c.user_id = %s",
        (session['user_id'],)
    )
    cart_items = cursor.fetchall()
    total = sum(item[2] for item in cart_items)
    
    if request.method == 'POST':
        cursor.execute("SELECT balance, delivery_address FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        if not user[1]:
            response = make_response(jsonify({"message": "Please set a delivery address"}), 400)
            return apply_security_headers(response)
        if user[0] < total:
            response = make_response(jsonify({"message": "Insufficient balance"}), 400)
            return apply_security_headers(response)
        
        cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (total, session['user_id']))
        cursor.execute("INSERT INTO orders (user_id, total) VALUES (%s, %s) RETURNING id", (session['user_id'], total))
        order_id = cursor.fetchone()[0]
        cursor.execute("DELETE FROM cart WHERE user_id = %s", (session['user_id'],))
        conn.commit()
        
        print(f"Purchase successful: Order ID {order_id}, Total ${total}, Address: {user[1]}")
        response = make_response(jsonify({"message": "Purchase successful"}))
        return apply_security_headers(response)
    
    response = make_response(render_template('checkout.html', cart_items=cart_items, total=total, inject_script=INJECT_SCRIPT, script_content=SCRIPT_CONTENT))
    return apply_security_headers(response)

if __name__ == '__main__':
    app.run(debug=True)
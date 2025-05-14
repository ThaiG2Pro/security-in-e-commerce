# user_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import hashlib
import uuid
import psycopg2
from models import get_db_connection, is_db_empty
from utils import add_security_headers

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
def index():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM products ORDER BY id DESC')
    products = c.fetchall()
    conn.close()
    return render_template('index.html', products=products, user=session.get('user'))

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    add_security_headers()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')
        if role not in ['user', 'admin']:
            role = 'user'
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        token = str(uuid.uuid4())
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (email, password, verified, balance, role) VALUES (%s, %s, %s, %s, %s)',
                      (email, hashed_password, 0, 10000000, role))
            c.execute('INSERT INTO verification (email, token) VALUES (%s, %s)',
                      (email, token))
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()
            return jsonify({'error': 'Email already exists'}), 400
        finally:
            conn.close()
        host = request.headers.get('Host')
        verify_link = f'http://{host}/verify?email={email}&token={token}'
        print(f'Verification link for {email}: {verify_link}')
        return jsonify({'message': 'Registration successful. Check console for verification link.'})
    return render_template('register.html')

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    add_security_headers()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT email, verified, role FROM users WHERE email = %s AND password = %s',
                  (email, hashed_password))
        user = c.fetchone()
        conn.close()
        if user:
            if user[1] == 0:
                return jsonify({'error': 'User not verified. Please check your email for the verification link.'}), 403
            session['user'] = email
            session['role'] = user[2]
            return jsonify({'message': 'Login successful'})
        return jsonify({'error': 'Invalid email or password'}), 401
    return render_template('login.html')

@user_bp.route('/logout')
def logout():
    add_security_headers()
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('index'))

@user_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    add_security_headers()
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT email FROM users WHERE email = %s', (email,))
        if c.fetchone():
            token = str(uuid.uuid4())
            c.execute('INSERT INTO reset_tokens (email, token) VALUES (%s, %s)',
                      (email, token))
            conn.commit()
            host = request.headers.get('Host')
            reset_link = f'http://{host}/reset/{token}'
            print(f'Reset password link for {email}: {reset_link}')
            conn.close()
            return jsonify({'message': 'Reset link sent. Check console.'})
        conn.close()
        return jsonify({'error': 'Email not found'}), 404
    return render_template('reset.html')

@user_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_confirm(token):
    add_security_headers()
    if request.method == 'POST':
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT email FROM reset_tokens WHERE token = %s', (token,))
        result = c.fetchone()
        if result:
            email = result[0]
            c.execute('UPDATE users SET password = %s, verified = 1 WHERE email = %s',
                      (hashed_password, email))
            c.execute('DELETE FROM reset_tokens WHERE token = %s', (token,))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Password reset successful'})
        conn.close()
        return jsonify({'error': 'Invalid token'}), 400
    return render_template('reset_confirm.html', token=token)

@user_bp.route('/verify')
def verify():
    add_security_headers()
    email = request.args.get('email')
    token = request.args.get('token')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT token FROM verification WHERE email = %s', (email,))
    stored_token = c.fetchone()
    if stored_token and stored_token[0] == token:
        c.execute('UPDATE users SET verified = 1 WHERE email = %s', (email,))
        c.execute('DELETE FROM verification WHERE email = %s', (email,))
        conn.commit()
        conn.close()
        return render_template('verify.html', message='Email verified successfully')
    conn.close()
    return render_template('verify.html', message='Invalid verification link'), 404

@user_bp.route('/cart')
def cart():
    add_security_headers()
    if 'user' not in session:
        return redirect(url_for('login'))
    email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT p.*, pv.variant_type, pv.variant_value, pv.price_modifier, c.quantity FROM products p JOIN cart c ON p.id = c.product_id LEFT JOIN product_variants pv ON pv.id = c.product_variant_id WHERE c.user_email = %s''', (email,))
    cart_items = c.fetchall()
    total = 0
    for item in cart_items:
        price = float(item[3])
        if item[-2]:
            price += float(item[-2])
        total += price * (item[-1] or 1)
    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total, user=session.get('user'))

@user_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    add_security_headers()
    if 'user' not in session:
        return jsonify({'error': 'Please login to add items to cart'}), 401
    product_id = request.form['product_id']
    variant_id = request.form.get('variant_id')
    quantity = int(request.form.get('quantity', 1))
    email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO cart (user_email, product_id, product_variant_id, quantity) VALUES (%s, %s, %s, %s)
                     ON CONFLICT (user_email, product_id, product_variant_id) DO UPDATE SET quantity = cart.quantity + EXCLUDED.quantity''',
                  (email, product_id, variant_id, quantity))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
    conn.close()
    return jsonify({'message': 'Added to cart'})

@user_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    add_security_headers()
    if 'user' not in session:
        return redirect(url_for('login'))
    email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT p.*, pv.variant_type, pv.variant_value, pv.price_modifier, c.quantity FROM products p JOIN cart c ON p.id = c.product_id LEFT JOIN product_variants pv ON pv.id = c.product_variant_id WHERE c.user_email = %s''', (email,))
    cart_items = c.fetchall()
    total = 0
    for item in cart_items:
        price = float(item[3])
        if item[-2]:
            price += float(item[-2])
        total += price * (item[-1] or 1)
    c.execute('SELECT balance FROM users WHERE email = %s', (email,))
    balance = c.fetchone()[0]
    if request.method == 'POST':
        if not cart_items:
            conn.close()
            return jsonify({'error': 'Cart is empty'}), 400
        if total > balance:
            conn.close()
            return jsonify({'error': 'Insufficient balance'}), 400
        order_id = str(uuid.uuid4())
        c.execute('''INSERT INTO orders (id, user_email, status, total) VALUES (%s, %s, %s, %s)''',
                  (order_id, email, 'pending', total))
        for item in cart_items:
            product_id = item[0]
            product_variant_id = item[-3] if len(item) > 15 else None
            quantity = item[-1] or 1
            price = float(item[3])
            if item[-2]:
                price += float(item[-2])
            c.execute('''INSERT INTO order_items (order_id, product_id, product_variant_id, quantity, price) VALUES (%s, %s, %s, %s, %s)''',
                      (order_id, product_id, product_variant_id, quantity, price))
        c.execute('UPDATE users SET balance = balance - %s WHERE email = %s', (total, email))
        c.execute('DELETE FROM cart WHERE user_email = %s', (email,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Purchase successful', 'order_id': order_id})
    conn.close()
    return render_template('checkout.html', cart_items=cart_items, total=total, user=email)

@user_bp.route('/wishlist', methods=['GET'])
def wishlist():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM wishlists WHERE user_email = %s', (user_email,))
    wishlist_items = c.fetchall()
    conn.close()
    return render_template('wishlist.html', wishlist_items=wishlist_items, user=user_email)

@user_bp.route('/orders')
def order_history():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE user_email = %s ORDER BY created_at DESC', (user_email,))
    orders = c.fetchall()
    conn.close()
    return render_template('orders.html', orders=orders, user=user_email)

@user_bp.route('/order/<order_id>')
def order_detail(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE id = %s AND user_email = %s', (order_id, user_email))
    order = c.fetchone()
    c.execute('SELECT * FROM order_items WHERE order_id = %s', (order_id,))
    items = c.fetchall()
    conn.close()
    return render_template('order_detail.html', order=order, items=items, user=user_email)

@user_bp.route('/account/addresses', methods=['GET', 'POST'])
def manage_addresses():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'POST':
        address_data = [
            request.form['address_line1'],
            request.form.get('address_line2', ''),
            request.form['city'],
            request.form.get('state', ''),
            request.form['postal_code'],
            request.form['country'],
            request.form.get('is_default', False),
            request.form.get('address_type', 'shipping')
        ]
        c.execute('''INSERT INTO user_addresses (user_email, address_line1, address_line2, city, state, postal_code, country, is_default, address_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                  (user_email, *address_data))
        conn.commit()
    c.execute('SELECT * FROM user_addresses WHERE user_email = %s', (user_email,))
    addresses = c.fetchall()
    conn.close()
    return render_template('addresses.html', addresses=addresses, user=user_email)

@user_bp.route('/account/payment-methods', methods=['GET', 'POST'])
def manage_payment_methods():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'POST':
        payment_data = [
            request.form['payment_type'],
            request.form['provider'],
            request.form['account_number'],
            request.form['expiry_date'],
            request.form.get('is_default', False)
        ]
        c.execute('''INSERT INTO user_payment_methods (user_email, payment_type, provider, account_number, expiry_date, is_default) VALUES (%s, %s, %s, %s, %s, %s)''',
                  (user_email, *payment_data))
        conn.commit()
    c.execute('SELECT * FROM user_payment_methods WHERE user_email = %s', (user_email,))
    payment_methods = c.fetchall()
    conn.close()
    return render_template('payment_methods.html', payment_methods=payment_methods, user=user_email)

@user_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = c.fetchone()
    c.execute('SELECT * FROM product_variants WHERE product_id = %s', (product_id,))
    variants = c.fetchall()
    c.execute('SELECT * FROM product_reviews WHERE product_id = %s', (product_id,))
    reviews = c.fetchall()
    conn.close()
    return render_template('product_detail.html', product=product, variants=variants, reviews=reviews, user=session.get('user'))

@user_bp.route('/shop')
def shop():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM products ORDER BY id DESC')
    products = c.fetchall()
    c.execute('SELECT * FROM product_categories ORDER BY name')
    categories = c.fetchall()
    conn.close()
    return render_template('shop.html', products=products, categories=categories, user=session.get('user'))

@user_bp.route('/about')
def about():
    return render_template('about.html', user=session.get('user'))

@user_bp.route('/faq')
def faq():
    return render_template('faq.html', user=session.get('user'))

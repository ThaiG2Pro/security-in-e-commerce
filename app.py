from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
import hashlib
import uuid
import os
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# Kết nối PostgreSQL
def get_db_connection():
    db_url = os.getenv('DATABASE_URL')
    parsed_url = urlparse(db_url)
    conn = psycopg2.connect(
        database=parsed_url.path[1:],
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port
    )
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id SERIAL PRIMARY KEY, name TEXT, price REAL, image TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password TEXT, verified INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id TEXT PRIMARY KEY, email TEXT, items TEXT, total REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS verification
                 (email TEXT PRIMARY KEY, token TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reset_tokens
                 (email TEXT PRIMARY KEY, token TEXT)''')
    # Thêm sản phẩm từ thư mục static/images
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        image_dir = 'static/images'
        if os.path.exists(image_dir):
            for img in os.listdir(image_dir):
                if img.lower().endswith('.jpg'):
                    name = img.replace('.jpg', '').capitalize()
                    c.execute('INSERT INTO products (name, price, image) VALUES (%s, %s, %s)',
                              (name, 10.0, f'images/{img}'))
    conn.commit()
    conn.close()

# Khởi tạo database
init_db()

# Trang chủ (danh sách sản phẩm)
@app.route('/')
def index():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM products')
    products = c.fetchall()
    conn.close()
    return render_template('index.html', products=products, user=session.get('user'))

# Đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT email, verified FROM users WHERE email = %s AND password = %s',
                  (email, hashed_password))
        user = c.fetchone()
        conn.close()
        if user:
            if user[1] == 0:
                return jsonify({'error': 'User not verified. Please check your email for the verification link.'}), 403
            session['user'] = email
            return jsonify({'message': 'Login successful'})
        return jsonify({'error': 'Invalid email or password'}), 401
    return render_template('login.html')

# Đăng xuất
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# Thêm vào giỏ hàng
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form['product_id']
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(product_id)
    session.modified = True
    return jsonify({'message': 'Added to cart'})

# Trang giỏ hàng
@app.route('/cart')
def cart():
    cart_items = []
    total = 0
    if 'cart' in session:
        conn = get_db_connection()
        c = conn.cursor()
        for pid in session['cart']:
            c.execute('SELECT * FROM products WHERE id = %s', (pid,))
            product = c.fetchone()
            if product:
                cart_items.append(product)
                total += product[2]
        conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total, user=session.get('user'))

# Trang thanh toán
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user' not in session:
        return redirect(url_for('login'))
    cart_items = cart_items_helper()
    total = sum([float(p[2]) for p in cart_items])
    if request.method == 'POST':
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400
        email = session['user']
        conn = get_db_connection()
        c = conn.cursor()
        items = ','.join(session['cart'])
        order_id = str(uuid.uuid4())
        c.execute('INSERT INTO orders (id, email, items, total) VALUES (%s, %s, %s, %s)',
                  (order_id, email, items, total))
        conn.commit()
        conn.close()
        session.pop('cart', None)
        return jsonify({'message': 'Purchase successful', 'order_id': order_id})
    return render_template('checkout.html', cart_items=cart_items, total=total, user=session.get('user'))

# Đăng ký
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        token = str(uuid.uuid4())
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (email, password, verified) VALUES (%s, %s, %s)',
                      (email, hashed_password, 0))
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

# Xác minh email
@app.route('/verify')
def verify():
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

# Quên mật khẩu
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT email FROM users WHERE email = %s', (email,))
        if c.fetchone():
            token = str(uuid.uuid4())
            c.execute('INSERT OR REPLACE INTO reset_tokens (email, token) VALUES (%s, %s)',
                      (email, token))
            conn.commit()
            host = request.headers.get('Host')  # Không kiểm tra Host header
            reset_link = f'http://{host}/reset/{token}'
            print(f'Reset password link for {email}: {reset_link}')
            conn.close()
            return jsonify({'message': 'Reset link sent. Check console.'})
        conn.close()
        return jsonify({'error': 'Email not found'}), 404
    return render_template('reset.html')

# Xác nhận reset mật khẩu
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_confirm(token):
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
                      (hashed_password, email))  # Tự động xác minh
            c.execute('DELETE FROM reset_tokens WHERE token = %s', (token,))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Password reset successful'})
        conn.close()
        return jsonify({'error': 'Invalid token'}), 400
    return render_template('reset_confirm.html', token=token)

# Helper: Lấy giỏ hàng
def cart_items_helper():
    cart_items = []
    if 'cart' in session:
        conn = get_db_connection()
        c = conn.cursor()
        for pid in session['cart']:
            c.execute('SELECT * FROM products WHERE id = %s', (pid,))
            product = c.fetchone()
            if product:
                cart_items.append(product)
        conn.close()
    return cart_items

if __name__ == '__main__':
    app.run(debug=True)
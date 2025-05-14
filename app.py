from flask import Flask, render_template, request, redirect, url_for, session, jsonify, after_this_request
import psycopg2
import hashlib
import uuid
import os
from urllib.parse import urlparse, unquote

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# Khởi tạo database (for local development and first-time production setup)
def is_db_empty():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT to_regclass('public.users')")
    exists = c.fetchone()[0] is not None
    conn.close()
    return not exists

if os.getenv('FLASK_ENV', 'development') == 'development' or is_db_empty():
    def init_db():
        conn = get_db_connection()
        c = conn.cursor()
        # Product categories
        c.execute('''CREATE TABLE IF NOT EXISTS product_categories (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            parent_id INTEGER REFERENCES product_categories(id)
        )''')
        # Products
        c.execute('''CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            sale_price REAL,
            sku TEXT UNIQUE,
            stock_quantity INTEGER DEFAULT 0,
            image TEXT,
            weight REAL,
            dimensions TEXT,
            category_id INTEGER REFERENCES product_categories(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Product variants
        c.execute('''CREATE TABLE IF NOT EXISTS product_variants (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            variant_type TEXT,
            variant_value TEXT,
            price_modifier REAL DEFAULT 0,
            sku TEXT UNIQUE,
            stock_quantity INTEGER DEFAULT 0
        )''')
        # Product reviews
        c.execute('''CREATE TABLE IF NOT EXISTS product_reviews (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            user_email TEXT REFERENCES users(email) ON DELETE SET NULL,
            rating INTEGER CHECK (rating BETWEEN 1 AND 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Users
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            verified INTEGER DEFAULT 0,
            balance REAL DEFAULT 10000000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )''')
        # User addresses
        c.execute('''CREATE TABLE IF NOT EXISTS user_addresses (
            id SERIAL PRIMARY KEY,
            user_email TEXT REFERENCES users(email) ON DELETE CASCADE,
            address_line1 TEXT NOT NULL,
            address_line2 TEXT,
            city TEXT NOT NULL,
            state TEXT,
            postal_code TEXT NOT NULL,
            country TEXT NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            address_type TEXT
        )''')
        # User payment methods
        c.execute('''CREATE TABLE IF NOT EXISTS user_payment_methods (
            id SERIAL PRIMARY KEY,
            user_email TEXT REFERENCES users(email) ON DELETE CASCADE,
            payment_type TEXT,
            provider TEXT,
            account_number TEXT,
            expiry_date TEXT,
            is_default BOOLEAN DEFAULT FALSE
        )''')
        # Orders
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_email TEXT REFERENCES users(email) ON DELETE SET NULL,
            status TEXT DEFAULT 'pending',
            total REAL NOT NULL,
            shipping_address_id INTEGER REFERENCES user_addresses(id),
            billing_address_id INTEGER REFERENCES user_addresses(id),
            payment_method_id INTEGER REFERENCES user_payment_methods(id),
            shipping_fee REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            notes TEXT,
            tracking_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Order items
        c.execute('''CREATE TABLE IF NOT EXISTS order_items (
            id SERIAL PRIMARY KEY,
            order_id TEXT REFERENCES orders(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
            product_variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            discount REAL DEFAULT 0
        )''')
        # Cart
        c.execute('''CREATE TABLE IF NOT EXISTS cart (
            id SERIAL PRIMARY KEY,
            user_email TEXT REFERENCES users(email) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            product_variant_id INTEGER REFERENCES product_variants(id) ON DELETE CASCADE,
            quantity INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_email, product_id, product_variant_id)
        )''')
        # Wishlist
        c.execute('''CREATE TABLE IF NOT EXISTS wishlists (
            id SERIAL PRIMARY KEY,
            user_email TEXT REFERENCES users(email) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_email, product_id)
        )''')
        # Coupons
        c.execute('''CREATE TABLE IF NOT EXISTS coupons (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            discount_type TEXT NOT NULL,
            discount_value REAL NOT NULL,
            min_purchase REAL DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            usage_limit INTEGER,
            usage_count INTEGER DEFAULT 0
        )''')
        # Shipping methods
        c.execute('''CREATE TABLE IF NOT EXISTS shipping_methods (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            estimated_days TEXT
        )''')
        # Verification and reset tokens (unchanged)
        c.execute('''CREATE TABLE IF NOT EXISTS verification (
            email TEXT PRIMARY KEY, token TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS reset_tokens (
            email TEXT PRIMARY KEY, token TEXT)''')
        conn.commit()
        conn.close()

    def populate_sample_data():
        conn = get_db_connection()
        c = conn.cursor()
        # Add product categories if missing
        c.execute("SELECT COUNT(*) FROM product_categories")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO product_categories (name, description) VALUES (%s, %s)", ('Beverages', 'Drinks and coffee'))
            c.execute("INSERT INTO product_categories (name, description) VALUES (%s, %s)", ('Bakery', 'Cakes and pastries'))
        # Add products if missing
        c.execute("SELECT COUNT(*) FROM products")
        if c.fetchone()[0] < 10:
            c.execute("SELECT id FROM product_categories WHERE name = %s", ('Beverages',))
            beverages_id = c.fetchone()[0]
            image_dir = 'static/images'
            import os
            if os.path.exists(image_dir):
                for img in os.listdir(image_dir):
                    if img.lower().endswith('.jpg'):
                        name = img.replace('.jpg', '').capitalize()
                        c.execute('INSERT INTO products (name, price, image, description, sku, stock_quantity, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                                  (name, 10.0, f'images/{img}', f'Description for {name}', f'SKU-{name}', 100, beverages_id))
        # Add shipping methods if missing
        c.execute("SELECT COUNT(*) FROM shipping_methods")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO shipping_methods (name, description, price, estimated_days) VALUES (%s, %s, %s, %s)",
                      ('Standard', 'Regular shipping', 5.0, '3-5 days'))
            c.execute("INSERT INTO shipping_methods (name, description, price, estimated_days) VALUES (%s, %s, %s, %s)",
                      ('Express', 'Fast delivery', 15.0, '1-2 days'))
        # Add sample coupons if missing
        c.execute("SELECT COUNT(*) FROM coupons")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO coupons (code, discount_type, discount_value, min_purchase, is_active) VALUES (%s, %s, %s, %s, %s)",
                      ('WELCOME10', 'percentage', 10, 0, True))
            c.execute("INSERT INTO coupons (code, discount_type, discount_value, min_purchase, is_active) VALUES (%s, %s, %s, %s, %s)",
                      ('FREESHIP', 'fixed', 5, 20, True))
        conn.commit()
        conn.close()

    init_db()
    populate_sample_data()
# In production, use Alembic migrations for future schema changes
# To migrate: alembic upgrade head

# Cấu hình session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Middleware cho Security Headers
def add_security_headers():
    if os.getenv('SECURITY_HEADERS', 'false').lower() == 'true':
        @after_this_request
        def set_headers(response):
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
            return response

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

# Mock data cho clickjacking
def get_mock_cart():
    return [
        (1, "Demo Shirt", 10.0, "images/shirt.jpg"),
        (2, "Demo Jeans", 10.0, "images/jeans.jpg")
    ]

# === Product Service Helpers ===
def get_products_by_category(category_id=None):
    conn = get_db_connection()
    c = conn.cursor()
    if category_id:
        c.execute('''SELECT p.*, pc.name as category_name FROM products p LEFT JOIN product_categories pc ON p.category_id = pc.id WHERE p.category_id = %s''', (category_id,))
    else:
        c.execute('''SELECT p.*, pc.name as category_name FROM products p LEFT JOIN product_categories pc ON p.category_id = pc.id''')
    products = c.fetchall()
    conn.close()
    return products

def get_product_variants(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM product_variants WHERE product_id = %s', (product_id,))
    variants = c.fetchall()
    conn.close()
    return variants

def get_product_reviews(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM product_reviews WHERE product_id = %s', (product_id,))
    reviews = c.fetchall()
    conn.close()
    return reviews

def add_product_review(product_id, user_email, rating, comment):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO product_reviews (product_id, user_email, rating, comment) VALUES (%s, %s, %s, %s)', (product_id, user_email, rating, comment))
    conn.commit()
    conn.close()

def get_user_wishlist(user_email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT p.* 
        FROM products p 
        JOIN wishlists w ON p.id = w.product_id 
        WHERE w.user_email = %s
    ''', (user_email,))
    wishlist_items = c.fetchall()
    conn.close()
    return wishlist_items

# === User Service Helpers ===
def get_user_addresses(user_email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM user_addresses WHERE user_email = %s', (user_email,))
    addresses = c.fetchall()
    conn.close()
    return addresses

def add_user_address(user_email, address_data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO user_addresses (user_email, address_line1, address_line2, city, state, postal_code, country, is_default, address_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''', (user_email, *address_data))
    conn.commit()
    conn.close()

def get_user_payment_methods(user_email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM user_payment_methods WHERE user_email = %s', (user_email,))
    payment_methods = c.fetchall()
    conn.close()
    return payment_methods

def add_payment_method(user_email, payment_data):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO user_payment_methods (user_email, payment_type, provider, account_number, expiry_date, is_default) VALUES (%s, %s, %s, %s, %s, %s)''', (user_email, *payment_data))
    conn.commit()
    conn.close()

# === Cart Service Helper (with variants and quantity) ===
def cart_items_helper(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT p.*, pv.variant_type, pv.variant_value, pv.price_modifier, c.quantity FROM products p JOIN cart c ON p.id = c.product_id LEFT JOIN product_variants pv ON pv.id = c.product_variant_id WHERE c.user_email = %s''', (email,))
    cart_items = c.fetchall()
    conn.close()
    return cart_items

# === Order Service Helper ===
def create_order(user_email, cart_items, shipping_address_id, billing_address_id, payment_method_id, shipping_fee=0, tax=0, discount=0, notes=''):
    conn = get_db_connection()
    c = conn.cursor()
    # Calculate total
    total = 0
    for item in cart_items:
        price = float(item[3])  # price
        if item[-2]:  # price_modifier if present
            price += float(item[-2])
        total += price * (item[-1] or 1)  # quantity
    total = total + shipping_fee + tax - discount
    # Create order
    order_id = str(uuid.uuid4())
    c.execute('''
        INSERT INTO orders 
        (id, user_email, status, total, shipping_address_id, billing_address_id, payment_method_id, shipping_fee, tax, discount, notes) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        order_id, 
        user_email, 
        'pending', 
        total, 
        shipping_address_id, 
        billing_address_id, 
        payment_method_id,
        shipping_fee,
        tax,
        discount,
        notes
    ))
    # Create order items
    for item in cart_items:
        product_id = item[0]
        product_variant_id = item[-3] if len(item) > 15 else None  # fallback for variant_id
        quantity = item[-1] or 1
        price = float(item[3])
        if item[-2]:
            price += float(item[-2])
        c.execute('''
            INSERT INTO order_items 
            (order_id, product_id, product_variant_id, quantity, price) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            order_id,
            product_id,
            product_variant_id,
            quantity,
            price
        ))
    # Update user balance
    c.execute('UPDATE users SET balance = balance - %s WHERE email = %s', (total, user_email))
    # Clear cart
    c.execute('DELETE FROM cart WHERE user_email = %s', (user_email,))
    conn.commit()
    conn.close()
    return order_id

# === Product Endpoints ===
@app.route('/')
def index():
    add_security_headers()
    category_id = request.args.get('category_id')
    products = get_products_by_category(category_id)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM product_categories')
    categories = c.fetchall()
    conn.close()
    return render_template('index.html', products=products, categories=categories, user=session.get('user'))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    add_security_headers()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = c.fetchone()
    conn.close()
    variants = get_product_variants(product_id)
    reviews = get_product_reviews(product_id)
    return render_template('product_detail.html', product=product, variants=variants, reviews=reviews, user=session.get('user'))

@app.route('/product/<int:product_id>/review', methods=['POST'])
def add_review(product_id):
    if 'user' not in session:
        return jsonify({'error': 'Please login to add a review'}), 401
    user_email = session['user']
    rating = int(request.form['rating'])
    comment = request.form['comment']
    conn = get_db_connection()
    c = conn.cursor()
    # Check if product exists
    c.execute('SELECT id FROM products WHERE id = %s', (product_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    # Check if user already reviewed this product
    c.execute('SELECT id FROM product_reviews WHERE product_id = %s AND user_email = %s', (product_id, user_email))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'You have already reviewed this product'}), 400
    # Add review
    c.execute('INSERT INTO product_reviews (product_id, user_email, rating, comment) VALUES (%s, %s, %s, %s)', (product_id, user_email, rating, comment))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Review added successfully'})

# Đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    add_security_headers()
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
    add_security_headers()
    session.pop('user', None)
    return redirect(url_for('index'))

# Thêm vào giỏ hàng
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    add_security_headers()
    clickjack = request.args.get('clickjack', 'false').lower() == 'true'
    if not clickjack and 'user' not in session:
        return jsonify({'error': 'Please login to add items to cart'}), 401
    product_id = request.form['product_id']
    variant_id = request.form.get('variant_id')  # Optional
    quantity = int(request.form.get('quantity', 1))
    email = session.get('user', 'demo@example.com' if clickjack else None)
    if clickjack:
        return jsonify({'message': 'Mock item added to cart'})
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

# Trang giỏ hàng
@app.route('/cart')
def cart():
    add_security_headers()
    clickjack = request.args.get('clickjack', 'false').lower() == 'true'
    if not clickjack and 'user' not in session:
        return redirect(url_for('login'))
    if clickjack:
        cart_items = get_mock_cart()
        total = sum([float(p[2]) for p in cart_items])
        return render_template('cart.html', cart_items=cart_items, total=total, user="Demo User")
    email = session['user']
    cart_items = cart_items_helper(email)
    total = 0
    for item in cart_items:
        price = float(item[3])  # price
        if item[-2]:  # price_modifier if present
            price += float(item[-2])
        total += price * (item[-1] or 1)  # quantity
    return render_template('cart.html', cart_items=cart_items, total=total, user=session.get('user'))

# Trang nhập địa chỉ giao hàng
@app.route('/delivery', methods=['GET', 'POST'])
def delivery():
    add_security_headers()
    clickjack = request.args.get('clickjack', 'false').lower() == 'true'
    if not clickjack and 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        address = request.form['address']
        session['delivery_address'] = address
        return redirect(url_for('checkout'))
    prefilled_address = unquote(request.args.get('address', ''))
    return render_template('delivery.html', prefilled_address=prefilled_address, user=session.get('user') or "Demo User")

# Trang thanh toán
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    add_security_headers()
    clickjack = request.args.get('clickjack', 'false').lower() == 'true'
    if not clickjack and 'user' not in session:
        return redirect(url_for('login'))
    email = session.get('user', 'demo@example.com' if clickjack else None)
    if clickjack:
        cart_items = get_mock_cart()
        total = sum([float(p[2]) for p in cart_items])
        balance = 10000000
    else:
        cart_items = cart_items_helper(email)
        total = 0
        for item in cart_items:
            price = float(item[3])  # price
            if item[-2]:  # price_modifier if present
                price += float(item[-2])
            total += price * (item[-1] or 1)  # quantity
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT balance FROM users WHERE email = %s', (email,))
        balance = c.fetchone()[0]
    if request.method == 'POST' and not clickjack:
        if not cart_items:
            if not clickjack:
                conn.close()
            return jsonify({'error': 'Cart is empty'}), 400
        if total > balance:
            if not clickjack:
                conn.close()
            return jsonify({'error': 'Insufficient balance'}), 400
        # For demo, use None for address/payment ids
        shipping_address_id = None
        billing_address_id = None
        payment_method_id = None
        shipping_fee = 0
        tax = 0
        discount = 0
        notes = ''
        order_id = create_order(email, cart_items, shipping_address_id, billing_address_id, payment_method_id, shipping_fee, tax, discount, notes)
        if not clickjack:
            conn.close()
        session.pop('delivery_address', None)
        return jsonify({'message': 'Purchase successful', 'order_id': order_id})
    if not clickjack:
        conn.close()
    inject_script = os.getenv('INJECT_SCRIPT', 'false').lower() == 'true'
    script_content = os.getenv('SCRIPT_CONTENT', '') if inject_script else ''
    return render_template('checkout.html', cart_items=cart_items, total=total, user=email,
                          inject_script=inject_script, script_content=script_content)

# Đăng ký
@app.route('/register', methods=['GET', 'POST'])
def register():
    add_security_headers()
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        token = str(uuid.uuid4())
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (email, password, verified, balance) VALUES (%s, %s, %s, %s)',
                      (email, hashed_password, 0, 10000000))
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

# Quên mật khẩu
@app.route('/reset-password', methods=['GET', 'POST'])
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

@app.route('/account/addresses', methods=['GET', 'POST'])
def manage_addresses():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
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
        add_user_address(user_email, address_data)
        return redirect(url_for('manage_addresses'))
    addresses = get_user_addresses(user_email)
    return render_template('addresses.html', addresses=addresses, user=user_email)

@app.route('/account/payment-methods', methods=['GET', 'POST'])
def manage_payment_methods():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    if request.method == 'POST':
        payment_data = [
            request.form['payment_type'],
            request.form['provider'],
            request.form['account_number'],
            request.form['expiry_date'],
            request.form.get('is_default', False)
        ]
        add_payment_method(user_email, payment_data)
        return redirect(url_for('manage_payment_methods'))
    payment_methods = get_user_payment_methods(user_email)
    return render_template('payment_methods.html', payment_methods=payment_methods, user=user_email)

@app.route('/wishlist', methods=['GET'])
def wishlist():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    wishlist_items = get_user_wishlist(user_email)
    return render_template('wishlist.html', wishlist_items=wishlist_items, user=user_email)

@app.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'user' not in session:
        return jsonify({'error': 'Please login to add to wishlist'}), 401
    user_email = session['user']
    product_id = request.form['product_id']
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO wishlists (user_email, product_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (user_email, product_id))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
    conn.close()
    return jsonify({'message': 'Added to wishlist'})

@app.route('/orders')
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

@app.route('/order/<order_id>')
def order_detail(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE id = %s AND user_email = %s', (order_id, user_email))
    order = c.fetchone()
    if not order:
        conn.close()
        return render_template('error.html', message='Order not found'), 404
    c.execute('''SELECT oi.*, p.name, p.image, pv.variant_type, pv.variant_value FROM order_items oi
                 LEFT JOIN products p ON oi.product_id = p.id
                 LEFT JOIN product_variants pv ON oi.product_variant_id = pv.id
                 WHERE oi.order_id = %s''', (order_id,))
    items = c.fetchall()
    conn.close()
    return render_template('order_detail.html', order=order, items=items, user=user_email)

if __name__ == '__main__':
    app.run(debug=True)
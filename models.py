# models.py
# Database connection and schema helpers moved from app.py
import os
import psycopg2
from urllib.parse import urlparse

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

def is_db_empty():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT to_regclass('public.users')")
    exists = c.fetchone()[0] is not None
    conn.close()
    return not exists

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Product categories
    c.execute('''CREATE TABLE IF NOT EXISTS product_categories (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT
    )''')
    # Products
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        image TEXT,
        description TEXT,
        sku TEXT UNIQUE,
        stock_quantity INTEGER DEFAULT 0,
        category_id INTEGER REFERENCES product_categories(id) ON DELETE SET NULL
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
        last_login TIMESTAMP,
        role TEXT NOT NULL DEFAULT 'user'
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
    # Verification and reset tokens
    c.execute('''CREATE TABLE IF NOT EXISTS verification (
        email TEXT PRIMARY KEY, token TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reset_tokens (
        email TEXT PRIMARY KEY, token TEXT)''')
    conn.commit()
    conn.close()

def populate_sample_data():
    import hashlib
    conn = get_db_connection()
    c = conn.cursor()
    # Add product categories if missing
    c.execute("SELECT COUNT(*) FROM product_categories")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO product_categories (name, description) VALUES (%s, %s)", ('Beverages', 'Drinks and coffee'))
        c.execute("INSERT INTO product_categories (name, description) VALUES (%s, %s)", ('Bakery', 'Cakes and pastries'))
    # Add products if missing
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] < 5:
        # Get category ids
        c.execute("SELECT id FROM product_categories WHERE name = %s", ('Beverages',))
        beverages_id = c.fetchone()[0]
        c.execute("SELECT id FROM product_categories WHERE name = %s", ('Bakery',))
        bakery_id = c.fetchone()[0]
        # Insert sample beverages
        c.execute('INSERT INTO products (name, price, image, description, sku, stock_quantity, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                  ('Bac Xiu', 18.0, 'images/bacxiu.jpg', 'Vietnamese iced coffee with condensed milk', 'SKU-BACXIU', 50, beverages_id))
        c.execute('INSERT INTO products (name, price, image, description, sku, stock_quantity, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                  ('Caphe Sua', 20.0, 'images/caphesua.jpg', 'Traditional Vietnamese coffee with milk', 'SKU-CAPHESUA', 60, beverages_id))
        c.execute('INSERT INTO products (name, price, image, description, sku, stock_quantity, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                  ('Tra Dao', 22.0, 'images/tradao.jpg', 'Peach tea with real fruit', 'SKU-TRADAO', 40, beverages_id))
        # Insert sample bakery
        c.execute('INSERT INTO products (name, price, image, description, sku, stock_quantity, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                  ('Banh Bong Lan', 25.0, 'images/banhbonglan.jpg', 'Soft sponge cake', 'SKU-BANHBONGLAN', 30, bakery_id))
        c.execute('INSERT INTO products (name, price, image, description, sku, stock_quantity, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                  ('Banh Chocolate', 28.0, 'images/banhchocolate.jpg', 'Rich chocolate cake', 'SKU-BANHCHOCOLATE', 25, bakery_id))
    # Add default admin user if missing
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    if c.fetchone()[0] == 0:
        admin_email = 'admin@example.com'
        admin_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (email, password, verified, balance, role) VALUES (%s, %s, %s, %s, %s)",
                  (admin_email, admin_password, 1, 10000000, 'admin'))
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

# Call sample data population on startup
defined = globals().get('populate_sample_data')
if defined:
    populate_sample_data()

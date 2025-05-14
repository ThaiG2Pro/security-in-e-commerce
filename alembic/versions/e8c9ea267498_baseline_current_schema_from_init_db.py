"""baseline: current schema from init_db

Revision ID: e8c9ea267498
Revises: 
Create Date: 2025-05-14 09:15:34.795441

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8c9ea267498'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Product categories
    op.execute('''CREATE TABLE IF NOT EXISTS product_categories (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        parent_id INTEGER REFERENCES product_categories(id)
    )''')
    # Products
    op.execute('''CREATE TABLE IF NOT EXISTS products (
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
    op.execute('''CREATE TABLE IF NOT EXISTS product_variants (
        id SERIAL PRIMARY KEY,
        product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
        variant_type TEXT,
        variant_value TEXT,
        price_modifier REAL DEFAULT 0,
        sku TEXT UNIQUE,
        stock_quantity INTEGER DEFAULT 0
    )''')
    # Product reviews
    op.execute('''CREATE TABLE IF NOT EXISTS product_reviews (
        id SERIAL PRIMARY KEY,
        product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
        user_email TEXT REFERENCES users(email) ON DELETE SET NULL,
        rating INTEGER CHECK (rating BETWEEN 1 AND 5),
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    # Users
    op.execute('''CREATE TABLE IF NOT EXISTS users (
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
    op.execute('''CREATE TABLE IF NOT EXISTS user_addresses (
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
    op.execute('''CREATE TABLE IF NOT EXISTS user_payment_methods (
        id SERIAL PRIMARY KEY,
        user_email TEXT REFERENCES users(email) ON DELETE CASCADE,
        payment_type TEXT,
        provider TEXT,
        account_number TEXT,
        expiry_date TEXT,
        is_default BOOLEAN DEFAULT FALSE
    )''')
    # Orders
    op.execute('''CREATE TABLE IF NOT EXISTS orders (
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
    op.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id TEXT REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
        product_variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        discount REAL DEFAULT 0
    )''')
    # Cart
    op.execute('''CREATE TABLE IF NOT EXISTS cart (
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
    op.execute('''CREATE TABLE IF NOT EXISTS wishlists (
        id SERIAL PRIMARY KEY,
        user_email TEXT REFERENCES users(email) ON DELETE CASCADE,
        product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_email, product_id)
    )''')
    # Coupons
    op.execute('''CREATE TABLE IF NOT EXISTS coupons (
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
    op.execute('''CREATE TABLE IF NOT EXISTS shipping_methods (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        estimated_days TEXT
    )''')
    # Verification and reset tokens
    op.execute('''CREATE TABLE IF NOT EXISTS verification (
        email TEXT PRIMARY KEY, token TEXT)''')
    op.execute('''CREATE TABLE IF NOT EXISTS reset_tokens (
        email TEXT PRIMARY KEY, token TEXT)''')


def downgrade() -> None:
    """Downgrade schema."""
    pass

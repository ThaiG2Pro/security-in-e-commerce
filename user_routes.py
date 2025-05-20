# user_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import hashlib
import uuid
import os
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
    return redirect(url_for('user.index'))

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
            # Hard-coded domain for security - prevents Host header attacks
            base_url = "http://localhost:5000" 
            reset_link = f"{base_url}/reset/{token}"
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
        return redirect(url_for('user.login'))
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

@user_bp.route('/update_cart', methods=['POST'])
def update_cart():
    add_security_headers()
    if 'user' not in session:
        return jsonify({'error': 'Please login to update cart'}), 401
    
    email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Process all form fields
        for key, value in request.form.items():
            if key.startswith('quantity_'):
                parts = key.split('_')
                if len(parts) >= 3:
                    product_id = parts[1]
                    variant_value = parts[2]
                    quantity = int(value)
                    
                    if quantity <= 0:
                        # Remove item if quantity is zero or negative
                        if variant_value == 'none':
                            c.execute("DELETE FROM cart WHERE user_email = %s AND product_id = %s AND product_variant_id IS NULL", 
                                     (email, product_id))
                        else:
                            c.execute("""DELETE FROM cart 
                                      WHERE user_email = %s AND product_id = %s 
                                      AND product_variant_id IN (SELECT id FROM product_variants 
                                                                WHERE variant_value = %s)""", 
                                     (email, product_id, variant_value))
                    else:
                        # Update quantity
                        if variant_value == 'none':
                            c.execute("UPDATE cart SET quantity = %s WHERE user_email = %s AND product_id = %s AND product_variant_id IS NULL", 
                                     (quantity, email, product_id))
                        else:
                            c.execute("""UPDATE cart SET quantity = %s 
                                      WHERE user_email = %s AND product_id = %s 
                                      AND product_variant_id IN (SELECT id FROM product_variants 
                                                                WHERE variant_value = %s)""", 
                                     (quantity, email, product_id, variant_value))
        
        conn.commit()
        
        # Recalculate totals to return updated cart data
        c.execute('''SELECT p.*, pv.variant_type, pv.variant_value, pv.price_modifier, c.quantity 
                   FROM products p JOIN cart c ON p.id = c.product_id 
                   LEFT JOIN product_variants pv ON pv.id = c.product_variant_id 
                   WHERE c.user_email = %s''', (email,))
        cart_items = c.fetchall()
        
        total = 0
        items_data = []
        
        for item in cart_items:
            price = float(item[3])
            if item[-2]:
                price += float(item[-2])
            subtotal = price * (item[-1] or 1)
            total += subtotal
            
            items_data.append({
                'product_id': item[0],
                'name': item[1],
                'quantity': item[-1],
                'price': price,
                'subtotal': subtotal,
                'variant_value': item[-3] or 'none'
            })
        
        return jsonify({
            'success': True,
            'items': items_data,
            'total': total
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@user_bp.route('/add_to_wishlist', methods=['POST'])
def add_to_wishlist():
    if 'user' not in session:
        return jsonify({'error': 'Please log in to add items to your wishlist'}), 401
    
    user_email = session['user']
    product_id = request.form.get('product_id')
    
    if not product_id:
        return jsonify({'error': 'Product ID is required'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Check if product exists
        c.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
        # Check if already in wishlist
        c.execute('SELECT * FROM wishlists WHERE user_email = %s AND product_id = %s', 
                 (user_email, product_id))
        if c.fetchone():
            conn.close()
            return jsonify({'message': 'Product already in your wishlist'})
        
        # Add to wishlist
        c.execute('INSERT INTO wishlists (user_email, product_id, added_at) VALUES (%s, %s, NOW())', 
                 (user_email, product_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Added to wishlist successfully'})
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/remove_from_wishlist', methods=['POST'])
def remove_from_wishlist():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    
    user_email = session['user']
    product_id = request.form.get('product_id')
    
    if not product_id:
        flash('Product not specified', 'error')
        return redirect(url_for('user.wishlist'))
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute(
            'DELETE FROM wishlist WHERE user_email = %s AND product_id = %s',
            (user_email, product_id)
        )
        conn.commit()
        flash('Product removed from wishlist', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error removing product from wishlist: {str(e)}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('user.wishlist'))

@user_bp.route('/delivery', methods=['GET', 'POST'])
def delivery():
    add_security_headers()
    if 'user' not in session:
        return redirect(url_for('user.login'))
    email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    
    # Handle form submission
    if request.method == 'POST':
        address = request.form.get('address', '')
        # For simplicity, we'll put the entire address in address_line1
        # In a real app, you would parse the address into components
        
        # Check if the user already has an address
        c.execute("SELECT * FROM user_addresses WHERE user_email = %s", (email,))
        existing_address = c.fetchone()
        
        if existing_address:
            # Update existing address
            c.execute("""UPDATE user_addresses 
                      SET address_line1 = %s, city = 'City', postal_code = '00000', country = 'Country'
                      WHERE user_email = %s""", 
                     (address, email))
        else:
            # Insert new address
            c.execute("""INSERT INTO user_addresses 
                      (user_email, address_line1, address_line2, city, state, postal_code, country) 
                      VALUES (%s, %s, '', 'City', 'State', '00000', 'Country')""", 
                     (email, address))
        
        conn.commit()
        # Redirect to checkout after successful address submission
        conn.close()
        return redirect(url_for('user.checkout'))
    
    # Fetch addresses for the user
    c.execute("SELECT * FROM user_addresses WHERE user_email = %s", (email,))
    addresses = c.fetchall()
    
    # Determine prefilled address
    prefilled_address = ''
    if addresses and len(addresses) > 0:
        prefilled_address = addresses[0][1]  # Assuming address is the second column
        # Determine prefilled address
    prefilled_address = ''
    if addresses and len(addresses) > 0:
        # Compile address from components
        address_parts = []
        if addresses[0][2]:  # address_line1
            address_parts.append(addresses[0][2])
        if addresses[0][3]:  # address_line2
            address_parts.append(addresses[0][3])
        if addresses[0][4]:  # city
            address_parts.append(addresses[0][4])
        if addresses[0][5]:  # state
            address_parts.append(addresses[0][5])
        if addresses[0][6]:  # postal_code
            address_parts.append(addresses[0][6])
        if addresses[0][7]:  # country
            address_parts.append(addresses[0][7])
        
        prefilled_address = ', '.join(filter(None, address_parts))
    
    conn.close()
    return render_template('delivery.html', user=session.get('user'), 
                          addresses=addresses, prefilled_address=prefilled_address)

@user_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    add_security_headers()
    if 'user' not in session:
        return redirect(url_for('user.login'))
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
    
    # Get user's addresses
    c.execute('SELECT * FROM user_addresses WHERE user_email = %s', (email,))
    addresses = c.fetchall()
    
    # Get user's payment methods
    c.execute('SELECT * FROM user_payment_methods WHERE user_email = %s', (email,))
    payment_methods = c.fetchall()
    
    conn.close()
    return render_template('checkout.html', 
                          cart_items=cart_items, 
                          total=total, 
                          user=email,
                          balance=balance,
                          addresses=addresses,
                          payment_methods=payment_methods)

@user_bp.route('/wishlist', methods=['GET'])
def wishlist():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    # Join wishlists with products to get all required product information
    c.execute('''
        SELECT p.id, p.name, p.price, p.description, w.added_at, w.id, p.image 
        FROM wishlists w 
        JOIN products p ON w.product_id = p.id 
        WHERE w.user_email = %s
        ORDER BY w.added_at DESC
    ''', (user_email,))
    wishlist_items = c.fetchall()
    conn.close()
    return render_template('wishlist.html', wishlist_items=wishlist_items, user=user_email)

@user_bp.route('/orders')
def order_history():
    if 'user' not in session:
        return redirect(url_for('user.login'))
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
        return redirect(url_for('user.login'))
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE id = %s AND user_email = %s', (order_id, user_email))
    order = c.fetchone()
    
    # Join order_items with products to get product details like name and image
    c.execute('''
        SELECT oi.*, p.name, p.image, pv.variant_type, pv.variant_value
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.id
        LEFT JOIN product_variants pv ON oi.product_variant_id = pv.id
        WHERE oi.order_id = %s
    ''', (order_id,))
    items = c.fetchall()
    conn.close()
    return render_template('order_detail.html', order=order, items=items, user=user_email)

@user_bp.route('/account/addresses', methods=['GET', 'POST'])
def manage_addresses():
    if 'user' not in session:
        return redirect(url_for('user.login'))
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
        return redirect(url_for('user.login'))
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

@user_bp.route('/product/<int:product_id>/review', methods=['POST'])
def add_product_review(product_id):
    if 'user' not in session:
        return jsonify({'error': 'Please log in to submit a review'}), 401
    
    user_email = session['user']
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    
    if not rating or not comment:
        return jsonify({'error': 'Rating and comment are required'}), 400
    
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid rating value'}), 400
    
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Check if product exists
        c.execute('SELECT * FROM products WHERE id = %s', (product_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
        
        # Add review
        c.execute(
            'INSERT INTO product_reviews (product_id, user_email, rating, comment, created_at) VALUES (%s, %s, %s, %s, NOW())',
            (product_id, user_email, rating, comment)
        )
        conn.commit()
        conn.close()
        return jsonify({'message': 'Review submitted successfully'})
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500

@user_bp.route('/shop')
def shop():
    conn = get_db_connection()
    c = conn.cursor()
    # Get column names from products table
    c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='products' ORDER BY ordinal_position")
    column_names = [row[0] for row in c.fetchall()]
    
    # Fetch products
    c.execute('SELECT * FROM products ORDER BY id DESC')
    products_data = c.fetchall()
    
    # Format product data with column names for easier access in template
    products = []
    
    for product in products_data:
        # Map tuple values to dictionary keys
        product_dict = {column_names[i]: product[i] for i in range(min(len(column_names), len(product)))}
        # Ensure image path is set correctly
        if product_dict.get('image'):
            # Make sure image doesn't have a path prefix already
            image_name = os.path.basename(product_dict['image'])
            product_dict['image'] = image_name
        products.append(product_dict)
    
    conn.close()
    return render_template('shop.html', products=products, user=session.get('user'))

@user_bp.route('/about')
def about():
    return render_template('about.html', user=session.get('user'))

@user_bp.route('/faq')
def faq():
    return render_template('faq.html', user=session.get('user'))

@user_bp.route('/account')
def account():
    if 'user' not in session:
        return redirect(url_for('user.login'))
    
    user_email = session['user']
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get user information
    c.execute('SELECT * FROM users WHERE email = %s', (user_email,))
    user_info = c.fetchone()
    
    # Get addresses
    c.execute('SELECT * FROM user_addresses WHERE user_email = %s LIMIT 3', (user_email,))
    addresses = c.fetchall()
    
    # Get payment methods
    c.execute('SELECT * FROM user_payment_methods WHERE user_email = %s LIMIT 3', (user_email,))
    payment_methods = c.fetchall()
    
    conn.close()
    return render_template('account.html', user=user_email, user_info=user_info, 
                           addresses=addresses, payment_methods=payment_methods)

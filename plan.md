# E-Commerce Application Enhancement Plan

## 1. Core Models and Helpers Update

### 1.1 Product Service
- **Implement product category support**
  ```python
  def get_products_by_category(category_id):
      conn = get_db_connection()
      c = conn.cursor()
      c.execute('SELECT p.*, pc.name as category_name FROM products p JOIN product_categories pc ON p.category_id = pc.id WHERE p.category_id = %s', (category_id,))
      products = c.fetchall()
      conn.close()
      return products
  ```

- **Add product variants support**
  ```python
  def get_product_variants(product_id):
      conn = get_db_connection()
      c = conn.cursor()
      c.execute('SELECT * FROM product_variants WHERE product_id = %s', (product_id,))
      variants = c.fetchall()
      conn.close()
      return variants
  ```

- **Implement product review functionality**
  ```python
  def add_product_review(product_id, user_email, rating, comment):
      conn = get_db_connection()
      c = conn.cursor()
      c.execute('INSERT INTO product_reviews (product_id, user_email, rating, comment) VALUES (%s, %s, %s, %s)',
                (product_id, user_email, rating, comment))
      conn.commit()
      conn.close()
  ```

### 1.2 User Service
- **Create address management helpers**
  ```python
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
      c.execute('''
          INSERT INTO user_addresses 
          (user_email, address_line1, address_line2, city, state, postal_code, country, is_default, address_type) 
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
      ''', (
          user_email, 
          address_data['address_line1'],
          address_data.get('address_line2', ''),
          address_data['city'],
          address_data.get('state', ''),
          address_data['postal_code'],
          address_data['country'],
          address_data.get('is_default', False),
          address_data.get('address_type', 'shipping')
      ))
      conn.commit()
      conn.close()
  ```

- **Implement payment method management**
  ```python
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
      c.execute('''
          INSERT INTO user_payment_methods 
          (user_email, payment_type, provider, account_number, expiry_date, is_default) 
          VALUES (%s, %s, %s, %s, %s, %s)
      ''', (
          user_email,
          payment_data['payment_type'],
          payment_data['provider'],
          payment_data['account_number'],
          payment_data.get('expiry_date', ''),
          payment_data.get('is_default', False)
      ))
      conn.commit()
      conn.close()
  ```

### 1.3 Cart Service
- **Update cart functionality for variants**
  ```python
  def update_cart_helper():
      # Replace current cart_items_helper with updated version
      def cart_items_helper(email):
          conn = get_db_connection()
          c = conn.cursor()
          c.execute('''
              SELECT p.*, pv.variant_type, pv.variant_value, pv.price_modifier, c.quantity
              FROM products p 
              JOIN cart c ON p.id = c.product_id
              LEFT JOIN product_variants pv ON pv.id = c.product_variant_id
              WHERE c.user_email = %s
          ''', (email,))
          cart_items = c.fetchall()
          conn.close()
          return cart_items
  ```

- **Add wishlist functionality**
  ```python
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
  ```

### 1.4 Order Service
- **Enhanced order creation process**
  ```python
  def create_order(user_email, cart_items, shipping_address_id, billing_address_id, payment_method_id, shipping_fee=0, tax=0, discount=0, notes=''):
      conn = get_db_connection()
      c = conn.cursor()
      
      # Calculate total
      total = sum([item[3] for item in cart_items])
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
          product_variant_id = item.get('variant_id')
          quantity = item.get('quantity', 1)
          price = item[3]
          
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
  ```

## 2. API Endpoints Update

### 2.1 Product Endpoints
- **Enhance product listing endpoint**
  ```python
  @app.route('/')
  def index():
      category_id = request.args.get('category_id')
      conn = get_db_connection()
      c = conn.cursor()
      
      if category_id:
          c.execute('''
              SELECT p.*, pc.name as category_name 
              FROM products p
              LEFT JOIN product_categories pc ON p.category_id = pc.id
              WHERE p.category_id = %s
          ''', (category_id,))
      else:
          c.execute('''
              SELECT p.*, pc.name as category_name 
              FROM products p
              LEFT JOIN product_categories pc ON p.category_id = pc.id
          ''')
      
      products = c.fetchall()
      
      # Get all categories for navigation
      c.execute('SELECT * FROM product_categories')
      categories = c.fetchall()
      
      conn.close()
      return render_template('index.html', products=products, categories=categories, user=session.get('user'))
  ```

- **Add product detail endpoint**
  ```python
  @app.route('/product/<int:product_id>')
  def product_detail(product_id):
      conn = get_db_connection()
      c = conn.cursor()
      
      # Get product details
      c.execute('''
          SELECT p.*, pc.name as category_name 
          FROM products p
          LEFT JOIN product_categories pc ON p.category_id = pc.id
          WHERE p.id = %s
      ''', (product_id,))
      product = c.fetchone()
      
      if not product:
          conn.close()
          return render_template('error.html', message='Product not found'), 404
      
      # Get product variants
      c.execute('SELECT * FROM product_variants WHERE product_id = %s', (product_id,))
      variants = c.fetchall()
      
      # Get product reviews
      c.execute('''
          SELECT pr.*, u.first_name, u.last_name 
          FROM product_reviews pr
          LEFT JOIN users u ON pr.user_email = u.email
          WHERE pr.product_id = %s
          ORDER BY pr.created_at DESC
      ''', (product_id,))
      reviews = c.fetchall()
      
      conn.close()
      return render_template('product_detail.html', product=product, variants=variants, reviews=reviews, user=session.get('user'))
  ```

- **Add product review endpoint**
  ```python
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
      c.execute('''
          INSERT INTO product_reviews (product_id, user_email, rating, comment)
          VALUES (%s, %s, %s, %s)
      ''', (product_id, user_email, rating, comment))
      
      conn.commit()
      conn.close()
      
      return jsonify({'message': 'Review added successfully'})
  ```

### 2.2 User Management Endpoints
- **Add address management endpoints**
  ```python
  @app.route('/account/addresses', methods=['GET', 'POST'])
  def manage_addresses():
      if 'user' not in session:
          return redirect(url_for('login'))
      
      user_email = session['user']
      
      if request.method == 'POST':
          address_data = {
              'address_line1': request.form['address_line1'],
              'address_line2': request.form.get('address_line2', ''),
              'city': request.form['city'],
              'state': request.form.get('state', ''),
              'postal_code': request.form['postal_code'],
              'country': request.form['country'],
              'is_default': 'is_default' in request.form,
              'address_type': request.form.get('address_type', 'shipping')
          }
          
          conn = get_db_connection()
          c = conn.cursor()
          
          # If this is set as default, unset other defaults of same type
          if address_data['is_default']:
              c.execute('''
                  UPDATE user_addresses 
                  SET is_default = FALSE 
                  WHERE user_email = %s AND address_type = %s AND is_default = TRUE
              ''', (user_email, address_data['address_type']))
          
          c.execute('''
              INSERT INTO user_addresses 
              (user_email, address_line1, address_line2, city, state, postal_code, country, is_default, address_type) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
          ''', (
              user_email, 
              address_data['address_line1'],
              address_data['address_line2'],
              address_data['city'],
              address_data['state'],
              address_data['postal_code'],
              address_data['country'],
              address_data['is_default'],
              address_data['address_type']
          ))
          
          conn.commit()
          conn.close()
          
          return redirect(url_for('manage_addresses'))
      
      conn = get_db_connection()
      c = conn.cursor()
      c.execute('SELECT * FROM user_addresses WHERE user_email = %s', (user_email,))
      addresses = c.fetchall()
      conn.close()
      
      return render_template('addresses.html', addresses=addresses, user=user_email)
  ```

- **Add payment method management endpoints**
  ```python
  @app.route('/account/payment-methods', methods=['GET', 'POST'])
  def manage_payment_methods():
      if 'user' not in session:
          return redirect(url_for('login'))
      
      user_email = session['user']
      
      if request.method == 'POST':
          payment_data = {
              'payment_type': request.form['payment_type'],
              'provider': request.form['provider'],
              'account_number': request.form['account_number'],
              'expiry_date': request.form.get('expiry_date', ''),
              'is_default': 'is_default' in request.form
          }
          
          conn = get_db_connection()
          c = conn.cursor()
          
          # If this is set as default, unset other defaults
          if payment_data['is_default']:
              c.execute('''
                  UPDATE user_payment_methods 
                  SET is_default = FALSE 
                  WHERE user_email = %s AND is_default = TRUE
              ''', (user_email,))
          
          c.execute('''
              INSERT INTO user_payment_methods 
              (user_email, payment_type, provider, account_number, expiry_date, is_default) 
              VALUES (%s, %s, %s, %s, %s, %s)
          ''', (
              user_email,
              payment_data['payment_type'],
              payment_data['provider'],
              payment_data['account_number'],
              payment_data['expiry_date'],
              payment_data['is_default']
          ))
          
          conn.commit()
          conn.close()
          
          return redirect(url_for('manage_payment_methods'))
      
      conn = get_db_connection()
      c = conn.cursor()
      c.execute('SELECT * FROM user_payment_methods WHERE user_email = %s', (user_email,))
      payment_methods = c.fetchall()
      conn.close()
      
      return render_template('payment_methods.html', payment_methods=payment_methods, user=user_email)
  ```

### 2.3 Shopping Cart Endpoints
- **Update cart endpoints to handle variants and quantities**
  ```python
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
          c.execute('''
              INSERT INTO cart (user_email, product_id, product_variant_id, quantity) 
              VALUES (%s, %s, %s, %s)
              ON CONFLICT (user_email, product_id, product_variant_id) 
              DO UPDATE SET quantity = cart.quantity + %s
          ''', (email, product_id, variant_id, quantity, quantity))
          conn.commit()
      except psycopg2.IntegrityError:
          conn.rollback()
      conn.close()
      
      return jsonify({'message': 'Added to cart'})
  ```

- **Add wishlist endpoints**
  ```python
  @app.route('/wishlist', methods=['GET'])
  def wishlist():
      if 'user' not in session:
          return redirect(url_for('login'))
      
      user_email = session['user']
      
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
      
      return render_template('wishlist.html', wishlist_items=wishlist_items, user=user_email)
      
  @app.route('/add_to_wishlist', methods=['POST'])
  def add_to_wishlist():
      if 'user' not in session:
          return jsonify({'error': 'Please login to add items to wishlist'}), 401
      
      user_email = session['user']
      product_id = request.form['product_id']
      
      conn = get_db_connection()
      c = conn.cursor()
      try:
          c.execute('''
              INSERT INTO wishlists (user_email, product_id) 
              VALUES (%s, %s)
          ''', (user_email, product_id))
          conn.commit()
          conn.close()
          return jsonify({'message': 'Added to wishlist'})
      except psycopg2.IntegrityError:
          conn.rollback()
          conn.close()
          return jsonify({'message': 'Item already in wishlist'})
  ```

### 2.4 Checkout and Order Endpoints
- **Update checkout process**
  ```python
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
          conn = get_db_connection()
          c = conn.cursor()
          
          # Get cart items with variants and quantities
          cart_items = cart_items_helper(email)
          
          # Calculate subtotal
          subtotal = sum([float(item[3]) * (1 + float(item[6] or 0)) * int(item[7]) for item in cart_items])
          
          # Get shipping methods
          c.execute('SELECT * FROM shipping_methods')
          shipping_methods = c.fetchall()
          
          # Get user addresses
          c.execute('SELECT * FROM user_addresses WHERE user_email = %s', (email,))
          addresses = c.fetchall()
          
          # Get user payment methods
          c.execute('SELECT * FROM user_payment_methods WHERE user_email = %s', (email,))
          payment_methods = c.fetchall()
          
          # Get user balance
          c.execute('SELECT balance FROM users WHERE email = %s', (email,))
          balance = c.fetchone()[0]
          
          # Get shipping fee from form or use default
          shipping_method_id = request.form.get('shipping_method_id')
          shipping_fee = 0
          if shipping_method_id:
              c.execute('SELECT price FROM shipping_methods WHERE id = %s', (shipping_method_id,))
              result = c.fetchone()
              if result:
                  shipping_fee = result[0]
          
          # Apply coupon if provided
          coupon_code = request.form.get('coupon_code')
          discount = 0
          if coupon_code:
              c.execute('''
                  SELECT * FROM coupons 
                  WHERE code = %s AND is_active = TRUE
                  AND (start_date IS NULL OR start_date <= CURRENT_TIMESTAMP)
                  AND (end_date IS NULL OR end_date >= CURRENT_TIMESTAMP)
                  AND (usage_limit IS NULL OR usage_count < usage_limit)
                  AND min_purchase <= %s
              ''', (coupon_code, subtotal))
              coupon = c.fetchone()
              if coupon:
                  discount_type = coupon[3]
                  discount_value = coupon[4]
                  if discount_type == 'percentage':
                      discount = subtotal * (discount_value / 100)
                  else:  # fixed amount
                      discount = discount_value
          
          # Calculate tax (example: 10%)
          tax = subtotal * 0.1
          
          # Calculate total
          total = subtotal + shipping_fee + tax - discount
      
      if request.method == 'POST' and not clickjack:
          if not cart_items:
              conn.close()
              return jsonify({'error': 'Cart is empty'}), 400
          
          if total > balance:
              conn.close()
              return jsonify({'error': 'Insufficient balance'}), 400
          
          # Get selected address and payment method
          shipping_address_id = request.form.get('shipping_address_id')
          billing_address_id = request.form.get('billing_address_id', shipping_address_id)
          payment_method_id = request.form.get('payment_method_id')
          
          # Create order
          order_id = str(uuid.uuid4())
          c.execute('''
              INSERT INTO orders 
              (id, user_email, status, total, shipping_address_id, billing_address_id, payment_method_id, shipping_fee, tax, discount) 
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
          ''', (
              order_id, 
              email, 
              'pending', 
              total, 
              shipping_address_id, 
              billing_address_id, 
              payment_method_id,
              shipping_fee,
              tax,
              discount
          ))
          
          # Create order items
          for item in cart_items:
              product_id = item[0]
              product_variant_id = item[5] if len(item) > 5 else None
              quantity = item[7] if len(item) > 7 else 1
              price = item[3]
              price_modifier = item[6] if len(item) > 6 else 0
              item_price = price * (1 + float(price_modifier or 0))
              
              c.execute('''
                  INSERT INTO order_items 
                  (order_id, product_id, product_variant_id, quantity, price) 
                  VALUES (%s, %s, %s, %s, %s)
              ''', (
                  order_id,
                  product_id,
                  product_variant_id,
                  quantity,
                  item_price
              ))
          
          # Update user balance
          c.execute('UPDATE users SET balance = balance - %s WHERE email = %s', (total, email))
          
          # Update coupon usage if applied
          if coupon_code and 'coupon' in locals() and coupon:
              c.execute('UPDATE coupons SET usage_count = usage_count + 1 WHERE id = %s', (coupon[0],))
          
          # Clear cart
          c.execute('DELETE FROM cart WHERE user_email = %s', (email,))
          
          conn.commit()
          conn.close()
          
          return jsonify({'message': 'Purchase successful', 'order_id': order_id})
      
      if not clickjack:
          conn.close()
      
      inject_script = os.getenv('INJECT_SCRIPT', 'false').lower() == 'true'
      script_content = os.getenv('SCRIPT_CONTENT', '') if inject_script else ''
      
      return render_template(
          'checkout.html',
          cart_items=cart_items,
          subtotal=subtotal if 'subtotal' in locals() else 0,
          shipping_methods=shipping_methods if 'shipping_methods' in locals() else [],
          addresses=addresses if 'addresses' in locals() else [],
          payment_methods=payment_methods if 'payment_methods' in locals() else [],
          shipping_fee=shipping_fee if 'shipping_fee' in locals() else 0,
          tax=tax if 'tax' in locals() else 0,
          discount=discount if 'discount' in locals() else 0,
          total=total,
          user=email,
          inject_script=inject_script,
          script_content=script_content
      )
  ```

- **Add order history endpoint**
  ```python
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
      
      # Get order details
      c.execute('SELECT * FROM orders WHERE id = %s AND user_email = %s', (order_id, user_email))
      order = c.fetchone()
      
      if not order:
          conn.close()
          return render_template('error.html', message='Order not found'), 404
      
      # Get order items
      c.execute('''
          SELECT oi.*, p.name, p.image, pv.variant_type, pv.variant_value
          FROM order_items oi
          JOIN products p ON oi.product_id = p.id
          LEFT JOIN product_variants pv ON oi.product_variant_id = pv.id
          WHERE oi.order_id = %s
      ''', (order_id,))
      items = c.fetchall()
      
      # Get shipping address
      shipping_address = None
      if order[4]:  # shipping_address_id
          c.execute('SELECT * FROM user_addresses WHERE id = %s', (order[4],))
          shipping_address = c.fetchone()
      
      # Get billing address
      billing_address = None
      if order[5]:  # billing_address_id
          c.execute('SELECT * FROM user_addresses WHERE id = %s', (order[5],))
          billing_address = c.fetchone()
      
      # Get payment method
      payment_method = None
      if order[6]:  # payment_method_id
          c.execute('SELECT * FROM user_payment_methods WHERE id = %s', (order[6],))
          payment_method = c.fetchone()
      
      conn.close()
      
      return render_template(
          'order_detail.html',
          order=order,
          items=items,
          shipping_address=shipping_address,
          billing_address=billing_address,
          payment_method=payment_method,
          user=user_email
      )
  ```

## 3. Templates and UI Update

### 3.1 Product Templates
- **Update product listing template**
  - Add category navigation sidebar
  - Show product categories
  - Add quick view functionality
  - Display sale prices and discounts
  - Add "Add to Wishlist" button

- **Create product detail template**
  - Display product images with gallery
  - Show product description, specifications, and price
  - Display variant selection dropdowns (color, size, etc.)
  - Show quantity selector
  - Display "Add to Cart" and "Add to Wishlist" buttons
  - Show product reviews section with ratings
  - Add review submission form

### 3.2 User Account Templates
- **Create account dashboard template**
  - Order history section
  - Profile information
  - Navigation to addresses and payment methods

- **Create address management template**
  - List of saved addresses
  - Form to add new addresses
  - Options to edit and delete addresses
  - Set default shipping and billing addresses

- **Create payment method template**
  - List of saved payment methods
  - Form to add new payment methods
  - Set default payment method

### 3.3 Cart and Checkout Templates
- **Update cart template**
  - Display product variants and attributes
  - Show quantity controls
  - Display per-item and total prices
  - Add coupon code input

- **Update checkout template**
  - Multi-step checkout process (shipping, payment, review)
  - Address selection and form
  - Payment method selection
  - Shipping method selection
  - Order summary with fees, taxes, and discounts
  - Terms and conditions acceptance

### 3.4 Order Templates
- **Create order history template**
  - List of past orders with status
  - Order date and total
  - Links to order details

- **Create order detail template**
  - Order status and tracking information
  - Order items with variants and quantities
  - Price breakdown
  - Shipping and billing information
  - Payment method used

## 4. Data Migration Implementation

### 4.1 Migration Strategy
- Create a migration script to run once after schema updates
- Ensure backward compatibility for existing data
- Handle null values and defaults for new columns

### 4.2 Sample Data Generation
```python
def populate_sample_data():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if we need to add sample data
    c.execute("SELECT COUNT(*) FROM product_categories")
    if c.fetchone()[0] == 0:
        # Add product categories
        categories = [
            ('Electronics', 'Electronic devices and accessories'),
            ('Clothing', 'Apparel and fashion items'),
            ('Home & Kitchen', 'Home goods and appliances'),
            ('Books', 'Books, e-books and publications')
        ]
        for name, description in categories:
            c.execute("INSERT INTO product_categories (name, description) VALUES (%s, %s) RETURNING id", (name, description))
            category_id = c.fetchone()[0]
            
            # Add subcategories
            if name == 'Electronics':
                subcategories = [('Smartphones', 'Mobile phones and accessories'), ('Laptops', 'Notebooks and accessories')]
            elif name == 'Clothing':
                subcategories = [('Men', 'Men\'s clothing'), ('Women', 'Women\'s clothing')]
            elif name == 'Home & Kitchen':
                subcategories = [('Kitchen', 'Kitchen appliances'), ('Furniture', 'Home furniture')]
            else:
                subcategories = [('Fiction', 'Fiction books'), ('Non-fiction', 'Non-fiction books')]
                
            for sub_name, sub_desc in subcategories:
                c.execute("INSERT INTO product_categories (name, description, parent_id) VALUES (%s, %s, %s)", 
                          (sub_name, sub_desc, category_id))
    
    # Check if we need to add sample products
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] < 10:  # Add more products if we have fewer than 10
        # Get category IDs
        c.execute("SELECT id, name FROM product_categories WHERE parent_id IS NOT NULL")
        subcategories = c.fetchall()
        
        # Sample products for each subcategory
        for category_id, category_name in subcategories:
            if 'Smartphones' in category_name:
                products = [
                    ('Smartphone X', 'Latest model with advanced features', 999.99, 949.99, 'PHONE-X-001', 50, 'smartphone.jpg', 0.4, '6.5 x 3.0 x 0.3 inches'),
                    ('Budget Phone', 'Affordable smartphone with good performance', 299.99, None, 'PHONE-B-002', 100, 'budget_phone.jpg', 0.35, '6.2 x 3.0 x 0.35 inches')
                ]
            elif 'Laptops' in category_name:
                products = [
                    ('UltraBook Pro', 'Lightweight professional laptop', 1299.99, 1199.99, 'LAPTOP-U-001', 30, 'ultrabook.jpg', 1.8, '13.3 x 8.9 x 0.6 inches'),
                    ('Gaming Laptop', 'High-performance gaming machine', 1799.99, None, 'LAPTOP-G-002', 20, 'gaming_laptop.jpg', 2.5, '15.6 x 10.2 x 1.0 inches')
                ]
            elif 'Men' in category_name:
                products = [
                    ('Men\'s T-Shirt', 'Comfortable cotton t-shirt', 24.99, 19.99, 'TSHIRT-M-001', 200, 'mens_tshirt.jpg', 0.2, 'Medium'),
                    ('Men\'s Jeans', 'Classic straight fit jeans', 49.99, None, 'JEANS-M-001', 150, 'mens_jeans.jpg', 0.5, '32W x 32L')
                ]
            elif 'Women' in category_name:
                products = [
                    ('Women\'s Blouse', 'Elegant button-up blouse', 39.99, 34.99, 'BLOUSE-W-001', 180, 'womens_blouse.jpg', 0.15, 'Medium'),
                    ('Women\'s Dress', 'Casual summer dress', 59.99, None, 'DRESS-W-001', 100, 'womens_dress.jpg', 0.3, 'Medium')
                ]
            elif 'Kitchen' in category_name:
                products = [
                    ('Coffee Maker', 'Programmable drip coffee maker', 79.99, 69.99, 'COFFEE-001', 60, 'coffee_maker.jpg', 2.0, '10 x 8 x 14 inches'),
                    ('Blender', 'High-speed countertop blender', 69.99, None, 'BLENDER-001', 50, 'blender.jpg', 3.0, '8 x 8 x 15 inches')
                ]
            elif 'Furniture' in category_name:
                products = [
                    ('Desk Chair', 'Ergonomic office chair', 149.99, 129.99, 'CHAIR-001', 40, 'desk_chair.jpg', 15.0, '26 x 26 x 38 inches'),
                    ('Coffee Table', 'Modern living room table', 199.99, None, 'TABLE-001', 25, 'coffee_table.jpg', 30.0, '40 x 20 x 18 inches')
                ]
            elif 'Fiction' in category_name:
                products = [
                    ('Mystery Novel', 'Bestselling mystery thriller', 14.99, 12.99, 'BOOK-M-001', 300, 'mystery_book.jpg', 0.5, '6 x 9 inches'),
                    ('Science Fiction', 'Epic space adventure', 16.99, None, 'BOOK-S-001', 250, 'scifi_book.jpg', 0.5, '6 x 9 inches')
                ]
            elif 'Non-fiction' in category_name:
                products = [
                    ('Cookbook', 'Gourmet recipes collection', 24.99, 22.99, 'BOOK-C-001', 150, 'cookbook.jpg', 0.8, '8 x 10 inches'),
                    ('Self-Help Book', 'Personal development guide', 19.99, None, 'BOOK-H-001', 200, 'selfhelp_book.jpg', 0.6, '6 x 9 inches')
                ]
            else:
                continue
                
            for name, description, price, sale_price, sku, stock, image, weight, dimensions in products:
                c.execute('''
                    INSERT INTO products 
                    (name, description, price, sale_price, sku, stock_quantity, image, weight, dimensions, category_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (name, description, price, sale_price, sku, stock, image, weight, dimensions, category_id))
                
                product_id = c.fetchone()[0]
                
                # Add variants for clothing products
                if 'T-Shirt' in name or 'Blouse' in name or 'Dress' in name or 'Jeans' in name:
                    # Add size variants
                    sizes = [('Size', 'Small', -5.0), ('Size', 'Medium', 0.0), ('Size', 'Large', 0.0), ('Size', 'X-Large', 5.0)]
                    for variant_type, variant_value, price_modifier in sizes:
                        variant_sku = f"{sku}-{variant_value[0]}"
                        c.execute('''
                            INSERT INTO product_variants 
                            (product_id, variant_type, variant_value, price_modifier, sku, stock_quantity) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (product_id, variant_type, variant_value, price_modifier, variant_sku, stock // len(sizes)))
                    
                    # Add color variants
                    if 'T-Shirt' in name:
                        colors = [('Color', 'Black', 0.0), ('Color', 'White', 0.0), ('Color', 'Blue', 0.0)]
                    elif 'Blouse' in name:
                        colors = [('Color', 'White', 0.0), ('Color', 'Black', 0.0), ('Color', 'Red', 2.0)]
                    elif 'Dress' in name:
                        colors = [('Color', 'Red', 0.0), ('Color', 'Black', 0.0), ('Color', 'Floral', 5.0)]
                    else:  # Jeans
                        colors = [('Color', 'Blue', 0.0), ('Color', 'Black', 0.0), ('Color', 'Gray', 0.0)]
                        
                    for variant_type, variant_value, price_modifier in colors:
                        variant_sku = f"{sku}-{variant_value[0]}"
                        c.execute('''
                            INSERT INTO product_variants 
                            (product_id, variant_type, variant_value, price_modifier, sku, stock_quantity) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (product_id, variant_type, variant_value, price_modifier, variant_sku, stock // len(colors)))
                
                # Add storage variants for electronics
                elif 'Smartphone' in name or 'Phone' in name:
                    storage_options = [('Storage', '64GB', 0.0), ('Storage', '128GB', 100.0), ('Storage', '256GB', 200.0)]
                    for variant_type, variant_value, price_modifier in storage_options:
                        variant_sku = f"{sku}-{variant_value[0:3]}"
                        c.execute('''
                            INSERT INTO product_variants 
                            (product_id, variant_type, variant_value, price_modifier, sku, stock_quantity) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (product_id, variant_type, variant_value, price_modifier, variant_sku, stock // len(storage_options)))
                
                elif 'Laptop' in name or 'UltraBook' in name:
                    config_options = [
                        ('Configuration', 'i5/8GB/256GB', 0.0), 
                        ('Configuration', 'i7/16GB/512GB', 300.0), 
                        ('Configuration', 'i9/32GB/1TB', 600.0)
                    ]
                    for variant_type, variant_value, price_modifier in config_options:
                        variant_sku = f"{sku}-{variant_value[0:2]}"
                        c.execute('''
                            INSERT INTO product_variants 
                            (product_id, variant_type, variant_value, price_modifier, sku, stock_quantity) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (product_id, variant_type, variant_value, price_modifier, variant_sku, stock // len(config_options)))
    
    # Add shipping methods if not exists
    c.execute("SELECT COUNT(*) FROM shipping_methods")
    if c.fetchone()[0] == 0:
        shipping_methods = [
            ('Standard Shipping', 'Delivery within 3-5 business days', 5.99, '3-5 days'),
            ('Express Shipping', 'Delivery within 2 business days', 12.99, '1-2 days'),
            ('Next Day Delivery', 'Delivery on the next business day', 19.99, 'Next day'),
            ('Free Shipping', 'Free standard shipping on eligible orders', 0.00, '5-7 days')
        ]
        for name, description, price, days in shipping_methods:
            c.execute('''
                INSERT INTO shipping_methods (name, description, price, estimated_days)
                VALUES (%s, %s, %s, %s)
            ''', (name, description, price, days))
    
    # Add sample coupons if not exists
    c.execute("SELECT COUNT(*) FROM coupons")
    if c.fetchone()[0] == 0:
        coupons = [
            ('WELCOME10', 'percentage', 10.0, 0.0, True, None, '2025-12-31', None, 0),
            ('FREESHIP', 'fixed', 5.99, 50.0, True, None, '2025-08-31', 1000, 0),
            ('SUMMER25', 'percentage', 25.0, 100.0, True, '2025-06-01', '2025-08-31', 500, 0)
        ]
        for code, type, value, min_purchase, is_active, start_date, end_date, usage_limit, usage_count in coupons:
            c.execute('''
                INSERT INTO coupons 
                (code, discount_type, discount_value, min_purchase, is_active, start_date, end_date, usage_limit, usage_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (code, type, value, min_purchase, is_active, start_date, end_date, usage_limit, usage_count))
    
    conn.commit()
    conn.close()
```

### 4.3 Data Migration Script
```python
def migrate_existing_data():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Migrate products: assign default category if missing
    c.execute("SELECT id FROM products WHERE category_id IS NULL")
    uncategorized = c.fetchall()
    if uncategorized:
        # Get or create a general category
        c.execute("SELECT id FROM product_categories WHERE name = 'General' LIMIT 1")
        result = c.fetchone()
        if result:
            general_category_id = result[0]
        else:
            c.execute("INSERT INTO product_categories (name, description) VALUES ('General', 'Uncategorized products') RETURNING id")
            general_category_id = c.fetchone()[0]
        
        # Assign general category to uncategorized products
        for product_id in uncategorized:
            c.execute("UPDATE products SET category_id = %s WHERE id = %s", (general_category_id, product_id[0]))
    
    # Update cart items that don't have quantity
    c.execute("SELECT id FROM cart WHERE quantity IS NULL")
    null_quantity_items = c.fetchall()
    for item_id in null_quantity_items:
        c.execute("UPDATE cart SET quantity = 1 WHERE id = %s", (item_id[0],))
    
    # Ensure all users have first_name and last_name
    c.execute("SELECT email FROM users WHERE first_name IS NULL OR last_name IS NULL")
    incomplete_users = c.fetchall()
    for email in incomplete_users:
        username = email[0].split('@')[0]
        c.execute("UPDATE users SET first_name = %s, last_name = 'User' WHERE email = %s", 
                 (username.capitalize(), email[0]))
    
    # Create tracking numbers for existing orders
    c.execute("SELECT id FROM orders WHERE tracking_number IS NULL")
    orders_without_tracking = c.fetchall()
    for order_id in orders_without_tracking:
        tracking = f"TRK-{uuid.uuid4().hex[:8].upper()}"
        c.execute("UPDATE orders SET tracking_number = %s WHERE id = %s", (tracking, order_id[0]))
    
    conn.commit()
    conn.close()
```

## 5. Testing Approach

### 5.1 Unit Testing
- Test individual helpers and utility functions
- Test database interactions
- Test calculation functions (totals, discounts, etc.)

### 5.2 Integration Testing
- Test user flows from product browse to checkout
- Test cart and order creation process
- Test payment and checkout flow

### 5.3 UI/UX Testing
- Test responsiveness on different devices
- Test form validations and error messages
- Test navigation and user journey

### 5.4 Security Testing
- Test authentication and authorization
- Test input validation and sanitization
- Test secure checkout process

### 5.5 Performance Testing
- Test page load times
- Test database query performance
- Test checkout process under load

## Implementation Timeline

1. **Week 1: Core Models and Helpers Update**
   - Implement product service enhancements
   - Update user management functionality
   - Enhance cart and order services

2. **Week 2: API Endpoints Update**
   - Implement product and category endpoints
   - Update cart and checkout endpoints
   - Add user account management endpoints

3. **Week 3: Templates and UI Update**
   - Create product detail page
   - Update cart and checkout flow
   - Implement user account dashboard

4. **Week 4: Data Migration and Testing**
   - Implement data migration
   - Add sample data
   - Perform testing and bug fixes

## Conclusion

This plan provides a comprehensive approach to updating the e-commerce application with more realistic features. By focusing on enhanced product management, improved user experience, and a more robust checkout process, the application will provide a much more realistic e-commerce experience. The implementation follows best practices for maintainable code, security, and performance, while ensuring a smooth migration path from the existing codebase.
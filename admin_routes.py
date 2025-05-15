# admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session
import os
from models import get_db_connection
from utils import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', user=session.get('user'))

@admin_bp.route('/products')
@admin_required
def admin_products():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM products ORDER BY id DESC')
    products = c.fetchall()
    conn.close()
    return render_template('admin_products.html', products=products, user=session.get('user'))

@admin_bp.route('/add-product', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        image = request.form['image']
        description = request.form['description']
        sku = request.form['sku']
        stock_quantity = request.form['stock_quantity']
        category_id = request.form['category_id']
        c.execute('''INSERT INTO products (name, price, image, description, sku, stock_quantity, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                  (name, price, image, description, sku, stock_quantity, category_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin.admin_products'))

    conn.close()
    return render_template('admin_add_product.html', user=session.get('user'))

@admin_bp.route('/delete_product/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}", 500
    finally:
        conn.close()
    return redirect(url_for('admin.admin_products'))

@admin_bp.route('/add-category', methods=['GET', 'POST'])
@admin_required
def admin_add_category():
    conn = get_db_connection()
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        c.execute('INSERT INTO product_categories (name, description) VALUES (%s, %s)', (name, description))
        conn.commit()
        conn.close()
        return redirect(url_for('admin.admin_categories'))
    conn.close()
    return render_template('admin_add_category.html', user=session.get('user'))

@admin_bp.route('/categories')
@admin_required
def admin_categories():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM product_categories ORDER BY id')
    categories = c.fetchall()
    conn.close()
    return render_template('admin_categories.html', categories=categories, user=session.get('user'))

@admin_bp.route('/upload-image', methods=['POST'])
@admin_required
def admin_upload_image():
    if 'image' not in request.files:
        return redirect(url_for('admin.admin_images'))
    image = request.files['image']
    if image.filename == '':
        return redirect(url_for('admin.admin_images'))
    # Save the image to the server or cloud storage
    image_path = os.path.join(os.path.dirname(__file__), 'static', 'images', image.filename)
    image.save(image_path)
    return redirect(url_for('admin.admin_images'))

@admin_bp.route('/images')
@admin_required
def admin_images():
    # For demo: list images in static/images
    import os
    image_dir = os.path.join(os.path.dirname(__file__), 'static', 'images')
    images = [f for f in os.listdir(image_dir) if f.endswith('.jpg') or f.endswith('.png')]
    return render_template('admin_images.html', images=images, user=session.get('user'))

@admin_bp.route('/admin_edit_product/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        image = request.form['image']
        description = request.form['description']
        sku = request.form['sku']
        stock_quantity = request.form['stock_quantity']
        category_id = request.form.get('category_id', None)
        
        c.execute('''UPDATE products SET name=%s, price=%s, image=%s, description=%s, 
                   sku=%s, stock_quantity=%s WHERE id=%s''',
                  (name, price, image, description, sku, stock_quantity, product_id))
        
        if category_id:
            c.execute('UPDATE products SET category_id=%s WHERE id=%s', (category_id, product_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('admin.admin_products'))
    
    # Get product data
    c.execute('SELECT * FROM products WHERE id=%s', (product_id,))
    product = c.fetchone()
    
    # Get categories for the dropdown
    c.execute('SELECT * FROM product_categories ORDER BY name')
    categories = c.fetchall()
    
    conn.close()
    
    if not product:
        return redirect(url_for('admin.admin_products'))
    
    return render_template('admin_edit_product.html', product=product, categories=categories, user=session.get('user'))

@admin_bp.route('/delete-category/<int:category_id>', methods=['POST'])
@admin_required
def delete_category(category_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        # First update any products that use this category to have no category
        c.execute('UPDATE products SET category_id = NULL WHERE category_id = %s', (category_id,))
        # Then delete the category
        c.execute('DELETE FROM product_categories WHERE id = %s', (category_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return f"An error occurred: {e}", 500
    finally:
        conn.close()
    return redirect(url_for('admin.admin_categories'))

@admin_bp.route('/edit-category/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_category(category_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        c.execute('UPDATE product_categories SET name = %s, description = %s WHERE id = %s', 
                  (name, description, category_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin.admin_categories'))
    
    c.execute('SELECT * FROM product_categories WHERE id = %s', (category_id,))
    category = c.fetchone()
    conn.close()
    
    if not category:
        return redirect(url_for('admin.admin_categories'))
    
    return render_template('admin_edit_category.html', category=category, user=session.get('user'))

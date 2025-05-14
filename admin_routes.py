# admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session
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
    return render_template('admin_add_product.html', categories=categories, user=session.get('user'))

@admin_bp.route('/delete-product/<int:product_id>', methods=['POST'])
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

@admin_bp.route('/categories')
@admin_required
def admin_categories():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM product_categories ORDER BY id DESC')
    categories = c.fetchall()
    conn.close()
    return render_template('admin_categories.html', categories=categories, user=session.get('user'))

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

@admin_bp.route('/upload-image', methods=['POST'])
@admin_required
def admin_upload_image():
    if 'image' not in request.files:
        return 'No image uploaded', 400
    image = request.files['image']
    if image.filename == '':
        return 'No selected file', 400
    # Save the image to the server or cloud storage
    image.save(f'uploads/{image.filename}')
    return 'Image uploaded successfully', 200

@admin_bp.route('/images')
@admin_required
def admin_images():
    # For demo: list images in static/images
    import os
    image_dir = os.path.join(os.path.dirname(__file__), 'static', 'images')
    images = [f for f in os.listdir(image_dir) if f.endswith('.jpg') or f.endswith('.png')]
    return render_template('admin_images.html', images=images, user=session.get('user'))

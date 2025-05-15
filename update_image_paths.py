#!/usr/bin/env python3
# update_image_paths.py
# Script to fix product image paths in the database

from models import get_db_connection

def update_image_paths():
    """Update product image paths to remove 'static/' prefix"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # First, get all products with image paths that start with 'static/'
    c.execute("SELECT id, image FROM products WHERE image LIKE 'static/%'")
    products_to_update = c.fetchall()
    
    # Update each product image path
    for product_id, image_path in products_to_update:
        new_path = image_path.replace('static/', '')
        c.execute("UPDATE products SET image = %s WHERE id = %s", (new_path, product_id))
        print(f"Updated product {product_id}: {image_path} -> {new_path}")
    
    # Commit the changes
    conn.commit()
    print(f"Updated {len(products_to_update)} product image paths")
    
    conn.close()
    
if __name__ == "__main__":
    update_image_paths()

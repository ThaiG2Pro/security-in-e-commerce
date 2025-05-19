#!/usr/bin/env python3
# A script to fix the image paths in the database
from models import get_db_connection

def fix_image_paths():
    """
    Update image paths in the products table to remove the 'static/' prefix
    so they can be correctly resolved with url_for('static', filename='images/...')
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get all products with image paths
        c.execute('SELECT id, image FROM products WHERE image IS NOT NULL')
        products = c.fetchall()
        
        print(f"Found {len(products)} products with images to fix")
        
        for product in products:
            product_id, image_path = product
            
            # Only process if it starts with 'static/'
            if image_path and image_path.startswith('static/'):
                # Extract just the filename
                filename = image_path.replace('static/', '')
                
                print(f"Updating product {product_id}: {image_path} -> {filename}")
                
                # Update the database
                c.execute('UPDATE products SET image = %s WHERE id = %s', (filename, product_id))
        
        conn.commit()
        print("Database updated successfully")
        
    except Exception as e:
        print(f"Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_image_paths()
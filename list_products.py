#!/usr/bin/env python3
# A simple script to list products in the database and verify the image paths

import os
import sys
from models import get_db_connection
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def list_products():
    """List all products in the database with their attributes"""
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print(f"DATABASE_URL: {os.environ.get('DATABASE_URL')}")
        sys.exit(1)
    
    c = conn.cursor()
    
    # Get column names
    c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='products' ORDER BY ordinal_position")
    column_names = [row[0] for row in c.fetchall()]
    
    # Fetch all products
    c.execute('SELECT * FROM products ORDER BY id DESC')
    products = c.fetchall()
    
    print(f"Found {len(products)} products")
    print("Column names:", column_names)
    
    # Display product info
    for i, product in enumerate(products):
        print(f"\nProduct {i+1}:")
        for j, col in enumerate(column_names[:len(product)]):
            print(f"  {col}: {product[j]}")
        
        # Check if image exists
        if product[3]:  # image is the 4th column (index 3)
            image_path = os.path.join('static/images', product[3])
            if os.path.exists(image_path):
                print(f"  Image exists at: {image_path}")
            else:
                print(f"  ⚠️ Image NOT found at: {image_path}")
    
    conn.close()

if __name__ == "__main__":
    list_products()

#!/usr/bin/env python3
# copy_images.py
# Script to copy product images from image_of_internet to static/images

import os
import shutil
from pathlib import Path

def copy_images():
    """Copy product images from image_of_internet to static/images"""
    # Define source and destination directories
    src_dir = Path('image_of_internet')
    dst_dir = Path('static/images')
    
    # Create destination directory if it doesn't exist
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    # Get list of all image files in source directory (excluding the Python script)
    image_files = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f)) and f != 'resize.py']
    
    # Copy each image file to the destination directory
    count = 0
    for img_file in image_files:
        src_path = src_dir / img_file
        dst_path = dst_dir / img_file
        
        # Skip if the file already exists in destination
        if not dst_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"Copied {img_file}")
            count += 1
    
    print(f"Copied {count} new images to static/images/")

if __name__ == "__main__":
    copy_images()

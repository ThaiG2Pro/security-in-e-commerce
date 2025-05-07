#!/usr/bin/env python3
import os
import argparse
from PIL import Image
import sys

def resize_image(input_path, output_path, size=(200, 200)):
    """Resize an image to the specified size and save it to the output path."""
    try:
        with Image.open(input_path) as img:
            # Resize the image
            resized_img = img.resize(size, Image.LANCZOS)
            # Save the resized image
            resized_img.save(output_path)
            return True
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        return False

def process_folder(input_folder, output_folder, size=(200, 200)):
    """Process all images in the input folder and save resized versions to the output folder."""
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Keep track of processed files
    total_files = 0
    successful_files = 0
    
    # Supported image formats
    supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
    
    # Process each file in the input folder
    for filename in os.listdir(input_folder):
        input_path = os.path.join(input_folder, filename)
        
        # Skip directories
        if os.path.isdir(input_path):
            continue
        
        # Check if the file is an image based on extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in supported_formats:
            continue
            
        # Set up output path
        output_path = os.path.join(output_folder, filename)
        
        # Process the image
        total_files += 1
        if resize_image(input_path, output_path, size):
            successful_files += 1
            print(f"Resized: {filename}")
    
    return total_files, successful_files

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Resize images in a folder to 200x200 pixels')
    parser.add_argument('input_folder', help='Path to folder containing images')
    parser.add_argument('output_folder', help='Path to folder where resized images will be saved')
    parser.add_argument('-s', '--size', nargs=2, type=int, default=[200, 200], 
                        metavar=('WIDTH', 'HEIGHT'), help='Output size (default: 200 200)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if input folder exists
    if not os.path.exists(args.input_folder):
        print(f"Error: Input folder '{args.input_folder}' does not exist.")
        sys.exit(1)
    
    # Process the folder
    print(f"Resizing images from '{args.input_folder}' to {args.size[0]}x{args.size[1]}...")
    total, successful = process_folder(args.input_folder, args.output_folder, tuple(args.size))
    
    # Print summary
    print("\nSummary:")
    print(f"Total image files processed: {total}")
    print(f"Successfully resized images: {successful}")
    print(f"Resized images saved to: {args.output_folder}")

if __name__ == "__main__":
    main()
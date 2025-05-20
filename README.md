<!-- filepath: /home/thai/Projects/5-2025/EC335/README.md -->
# E-Commerce Website

A simple e-commerce website built with Flask, SQLite, and Tailwind CSS for educational purposes.

## Overview

This project demonstrates a basic e-commerce platform with product listings, shopping cart, checkout process, and user authentication. It intentionally includes two security vulnerabilities (clickjacking and host header injection) for educational demonstration.

## Features

- **Product Listings:** Display products from images in static/images folder
- **Shopping Cart:** Add and manage items in your cart
- **User System:** Register, login, email verification, password reset
- **Responsive Design:** Mobile-friendly interface using Tailwind CSS
- **Demo Email System:** Links are logged to console instead of sent via email

## Quick Start

### Prerequisites
- Python 3.x
- pip

### Setup

1. **Clone the repository:**
   ```
   git clone https://github.com/ThaiG2Pro/security-in-e-commerce.git
   cd EC335
   ```

2. **Create virtual environment:**
   ```
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # OR
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

4. **Update the secret key:**
   - Open `app.py`
   - Replace `app.secret_key = 'your-secret-key'` with a random string

### Running the Application

1. **Start the server:**
   ```
   python app.py
   ```

2. **Access the website:**
   - Open your browser and go to http://localhost:5000
   - Browse products and add them to cart
   - Register at /register (check console for verification link)
   - Login at /login once verified
   - Test password reset at /reset-password

## Security Vulnerabilities (For Educational Purposes)

1. **Clickjacking:**    
   - The /checkout page can be embedded in an iframe
   - Test with: `<iframe src="http://<your-url>/checkout" width="100%" height="600px"></iframe>`

2. **Host Header Injection:**
   - The password reset and registration systems are vulnerable
   - Can be tested by modifying the Host header to a malicious domain

> **Warning:** Do not use this code in production without fixing these vulnerabilities!

## Troubleshooting

- **User not verified:** Check console for verification link or reset password
- **Email exists error:** Delete the user from database or reset password:
  ```
  sqlite3 database.db
  DELETE FROM users WHERE email = '<email>';
  DELETE FROM verification WHERE email = '<email>';
  DELETE FROM reset_tokens WHERE email = '<email>';
  ```
- **404 Not Found for links:** Ensure server is running and database entries match
- **No products:** Add .jpg images (200x200px) to static/images folder

## Contributing

Feel free to fork this repository and submit improvements. For security fixes, please test thoroughly to maintain the intended vulnerabilities for demonstration purposes.

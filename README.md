E-Commerce Website
This is a simple e-commerce website built with Flask, SQLite, and Tailwind CSS. It includes features like product listing, cart, checkout, user registration, login, email verification, and password reset. The project intentionally includes two security vulnerabilities (clickjacking and host header injection) for demonstration purposes.
Table of Contents

Features
Project Structure
Requirements
Setup Instructions
Running Locally
Deploying Online
Security Vulnerabilities
Troubleshooting
Contributing

Features

Product Listing: Automatically displays products based on .jpg images in static/images (200x200px).
Cart: Add products to cart and view cart contents.
Checkout: Confirm purchase with a dedicated checkout page (vulnerable to clickjacking).
User Authentication:
Register with email and password.
Verify email via a link (logged to console).
Login with session management.
Reset password via a link (vulnerable to host header injection).

Responsive Design: Built with Tailwind CSS for a clean, mobile-friendly interface.
Fake Email System: Verification and reset links are logged to the console instead of sent via email.

Setup Instructions

Clone the Repository (if using Git):
git clone https://github.com/ThaiG2Pro/security-in-e-commerce.git
cd EC335

Or create the project structure manually as shown above.

Create a Virtual Environment:
python3 -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows

Install Dependencies:
pip install -r requirements.txt

Update Secret Key:

Open app.py and replace app.secret_key = 'your-secret-key' with a random string (e.g., x7k9m2p8q5).

Running Locally

Activate Virtual Environment:
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows

Run the Application:
python app.py

Access the Website:

Open a browser and go to http://localhost:5000.
Test features:
Browse products and add to cart.
Register (/register), check console for verification link, and verify email.
Login (/login) with verified account.
Reset password (/reset-password), check console for reset link.
Proceed to checkout (/checkout) after adding items to cart.

Deploying Online
To deploy on Render.com:

Clickjacking:
The /checkout page lacks the X-Frame-Options header, allowing it to be embedded in an iframe.
Test by creating an HTML file with:<iframe src="http://<your-url>/checkout" width="100%" height="600px"></iframe>

Host Header Injection:
The /reset-password and /register routes use request.headers.get('Host') without validation, making reset/verification links vulnerable.
Test by modifying the Host header (e.g., using Burp Suite) to evil.com and checking the console for a link like http://evil.com/reset/<token>.

Warning: Do not use this code in production without fixing these vulnerabilities.
Troubleshooting

"User not verified" error:
Check the console for the verification link and access it.
Alternatively, reset the password (/reset-password), as it automatically verifies the account.

"Email already exists" error:
Delete the email from database.db:sqlite3 database.db
DELETE FROM users WHERE email = '<email>';
DELETE FROM verification WHERE email = '<email>';
DELETE FROM reset_tokens WHERE email = '<email>';

Or reset the password for the existing email.

"404 Not Found" for verification/reset links:
Ensure the server is running (python app.py).
Verify the link’s email and token match the database.
Create a new token if needed:sqlite3 database.db
INSERT INTO verification (email, token) VALUES ('<email>', 'new-token-123456');

Then access: http://localhost:5000/verify?email=<email>&token=new-token-123456.

Missing images:
Ensure static/images contains .jpg files (200x200px).
Delete database.db and rerun python app.py to regenerate products.

Contributing
Feel free to fork this repository, make improvements, and submit pull requests. For security fixes, please test thoroughly to maintain the intended vulnerabilities for demonstration purposes.

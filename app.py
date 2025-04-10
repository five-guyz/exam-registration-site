"""
CSN Exam Registration System - Flask Backend
Main application controller that handles:
- Routing between pages
- Form processing
- User authentication flow
"""

from flask import Flask, render_template, request, redirect, url_for

# Initialize the Flask application
app = Flask(__name__)

@app.route('/')
def index():
    ## Render the homepage (login screen)
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    """
    Handle login form submissions
    - Receives username/password from POST request
    - TODO: Add actual authentication logic
    - Currently prints credentials and redirects to confirmation
    """
    username = request.form['username']
    password = request.form['password']
    
    # Temporary debug output (remove in production)
    print(f"Username: {username}, Password: {password}")
    
    # TODO: Implement real authentication
    # TODO: Add session management
    
    return redirect(url_for('confirmation'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle registration flow:
    - GET: Show empty registration form
    - POST: Process form data and create account
    """
    if request.method == 'POST':
        # Extract form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        nshe_id = request.form['nshe_id']
        
        # TODO: Store data in database (MySQL)
        # TODO: Add input validation
        
        return redirect(url_for('confirmation'))
    
    # Show registration form for GET requests
    return render_template('register.html')

@app.route('/confirmation')
def confirmation():
    ## Display success page after login/registration
    return render_template('confirmation.html')

if __name__ == '__main__':
    # Debug features:
    # - Auto-reload on code changes
    # - Detailed error pages
    app.run(debug=True)
